import logging
import os
import hashlib
import shutil
from typing import Optional
import uuid
import tempfile

from flask import request

from app.modules.auth.services import AuthenticationService
from app.modules.dataset.models import DSViewRecord, DataSet, DSMetaData
from app.modules.dataset.repositories import (
    AuthorRepository,
    DOIMappingRepository,
    DSDownloadRecordRepository,
    DSMetaDataRepository,
    DSViewRecordRepository,
    DataSetRepository,
)
from app.modules.featuremodel.repositories import (
    FMMetaDataRepository,
    FeatureModelRepository,
)
from app.modules.hubfile.repositories import (
    HubfileDownloadRecordRepository,
    HubfileRepository,
    HubfileViewRecordRepository,
)
from core.services.BaseService import BaseService
from zipfile import ZipFile
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def calculate_checksum_and_size(file_path):
    file_size = os.path.getsize(file_path)
    with open(file_path, "rb") as file:
        content = file.read()
        hash_md5 = hashlib.md5(content).hexdigest()
        return hash_md5, file_size


class DataSetService(BaseService):
    def __init__(self):
        super().__init__(DataSetRepository())
        self.feature_model_repository = FeatureModelRepository()
        self.author_repository = AuthorRepository()
        self.dsmetadata_repository = DSMetaDataRepository()
        self.fmmetadata_repository = FMMetaDataRepository()
        self.dsdownloadrecord_repository = DSDownloadRecordRepository()
        self.hubfiledownloadrecord_repository = HubfileDownloadRecordRepository()
        self.hubfilerepository = HubfileRepository()
        self.dsviewrecord_repostory = DSViewRecordRepository()
        self.hubfileviewrecord_repository = HubfileViewRecordRepository()

    def move_feature_models(self, dataset: DataSet):
        current_user = AuthenticationService().get_authenticated_user()
        source_dir = current_user.temp_folder()

        working_dir = os.getenv("WORKING_DIR", "")
        dest_dir = os.path.join(
            working_dir, "uploads", f"user_{current_user.id}", f"dataset_{dataset.id}"
        )

        os.makedirs(dest_dir, exist_ok=True)

        for feature_model in dataset.feature_models:
            uvl_filename = feature_model.fm_meta_data.uvl_filename
            shutil.move(os.path.join(source_dir, uvl_filename), dest_dir)

    def get_synchronized(self, current_user_id: int) -> DataSet:
        return self.repository.get_synchronized(current_user_id)

    def get_unsynchronized(self, current_user_id: int) -> DataSet:
        return self.repository.get_unsynchronized(current_user_id)

    def get_unsynchronized_dataset(
        self, current_user_id: int, dataset_id: int
    ) -> DataSet:
        return self.repository.get_unsynchronized_dataset(current_user_id, dataset_id)

    def latest_synchronized(self):
        return self.repository.latest_synchronized()

    def count_synchronized_datasets(self):
        return self.repository.count_synchronized_datasets()

    def is_synchronized(self, dataset_id: int) -> bool:
        return self.repository.is_synchronized(dataset_id)

    def count_feature_models(self):
        return self.feature_model_service.count_feature_models()

    def count_authors(self) -> int:
        return self.author_repository.count()

    def count_dsmetadata(self) -> int:
        return self.dsmetadata_repository.count()

    def total_dataset_downloads(self) -> int:
        return self.dsdownloadrecord_repository.total_dataset_downloads()

    def total_dataset_views(self) -> int:
        return self.dsviewrecord_repostory.total_dataset_views()

    def get_dataset_name(self, dataset_id: int) -> str:
        return self.repository.get_dataset_name(dataset_id)

    def create_from_form(self, form, current_user,is_anonymous) -> DataSet:
        is_anonymous = form.is_anonymous.data
        main_author = {
            "name": f"{current_user.profile.surname}, {current_user.profile.name}",
            "affiliation": current_user.profile.affiliation,
            "orcid": current_user.profile.orcid,
        }
        try:
            logger.info(f"Creating dsmetadata...: {form.get_dsmetadata()}")
            dsmetadata = self.dsmetadata_repository.create(**form.get_dsmetadata())
            if not is_anonymous:
                for author_data in [main_author] + form.get_authors():
                    author = self.author_repository.create(
                        commit=False, ds_meta_data_id=dsmetadata.id, **author_data
                    )
                    dsmetadata.authors.append(author)

            dataset = self.create(
                commit=False, user_id=current_user.id, ds_meta_data_id=dsmetadata.id, is_anonymous=is_anonymous
            )

            for feature_model in form.feature_models:
                uvl_filename = feature_model.uvl_filename.data
                fmmetadata = self.fmmetadata_repository.create(
                    commit=False, **feature_model.get_fmmetadata()
                )
                if not is_anonymous:
                    for author_data in feature_model.get_authors():
                        author = self.author_repository.create(
                            commit=False, fm_meta_data_id=fmmetadata.id, **author_data
                        )
                        fmmetadata.authors.append(author)

                fm = self.feature_model_repository.create(commit=False, data_set_id=dataset.id, fm_meta_data_id=fmmetadata.id)

                # Archivos asociados al feature_model
                file_path = os.path.join(current_user.temp_folder(), uvl_filename)
                checksum, size = calculate_checksum_and_size(file_path)

                file = self.hubfilerepository.create(
                    commit=False,
                    name=uvl_filename,
                    checksum=checksum,
                    size=size,
                    feature_model_id=fm.id,
                )
                fm.files.append(file)
            
            # if is_anonymous:
            #     dataset.user_id = None
            self.repository.session.commit()
            
        except Exception as exc:
            logger.info(f"Exception creating dataset from form...: {exc}")
            self.repository.session.rollback()
            raise exc
        
        return dataset

    def update_dsmetadata(self, id, **kwargs):
        return self.dsmetadata_repository.update(id, **kwargs)

    def get_uvlhub_doi(self, dataset: DataSet) -> str:
        domain = os.getenv("DOMAIN", "localhost")
        return f"http://{domain}/doi/{dataset.ds_meta_data.dataset_doi}"

    def get_synchronized_datasets(self) -> list[tuple[str, str]]:
        datasets = []
        for user_dir in Path("uploads").glob("user_*"):
            for dataset_dir in user_dir.glob("dataset_*"):
                dataset_id = int(dataset_dir.name.split("_")[1])
                if self.is_synchronized(dataset_id):
                    dataset_name = self.get_dataset_name(dataset_id)
                    datasets.append((dataset_name, str(dataset_dir)))
        return datasets

    def generate_datasets_and_name_zip(self) -> tuple[str, str]:
        temp_dir = Path(tempfile.mkdtemp())
        zip_filename = (
            f"chocohub2_datasets_from_{datetime.now().strftime('%d_%m_%Y')}.zip"
        )
        zip_path = temp_dir / zip_filename

        with ZipFile(zip_path, "w") as zipf:
            for dataset_info in self.get_synchronized_datasets():
                dataset_name, dataset_path = dataset_info
                for file_path in Path(dataset_path).rglob("*"):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(dataset_path)
                        zipf.write(
                            file_path, arcname=Path(dataset_name) / relative_path
                        )

        return str(zip_path), zip_filename
    
    def toggle_anonymity(self, dataset_id: int, current_user) -> DataSet:
        dataset = self.repository.get_or_404(dataset_id)
        if dataset.user_id != current_user.id:
            raise PermissionError("You do not have permission to modify this dataset.")

        dataset.is_anonymous = not dataset.is_anonymous
        if not dataset.is_anonymous:
            # Reasignar el user_id y actualizar los autores si se hace público
            dataset.user_id = current_user.id
            main_author = {
                "name": f"{current_user.profile.surname}, {current_user.profile.name}",
                "affiliation": current_user.profile.affiliation,
                "orcid": current_user.profile.orcid,
            }
            # Eliminar autores anónimos existentes
            for author in dataset.ds_meta_data.authors:
                self.author_repository.delete(author)
            # Agregar el autor principal
            author = self.author_repository.create(
                commit=False, ds_meta_data_id=dataset.ds_meta_data.id, **main_author
            )
            dataset.ds_meta_data.authors.append(author)
        else:
            # Anonimizar el user_id y eliminar los autores si se hace anónimo
            dataset.user_id = None
            for author in dataset.ds_meta_data.authors:
                self.author_repository.delete(author)

        self.repository.session.commit()
        return dataset


class AuthorService(BaseService):
    def __init__(self):
        super().__init__(AuthorRepository())


class DSDownloadRecordService(BaseService):
    def __init__(self):
        super().__init__(DSDownloadRecordRepository())


class DSMetaDataService(BaseService):
    def __init__(self):
        super().__init__(DSMetaDataRepository())

    def update(self, id, **kwargs):
        return self.repository.update(id, **kwargs)

    def filter_by_doi(self, doi: str) -> Optional[DSMetaData]:
        return self.repository.filter_by_doi(doi)


class DSViewRecordService(BaseService):
    def __init__(self):
        super().__init__(DSViewRecordRepository())

    def the_record_exists(self, dataset: DataSet, user_cookie: str):
        return self.repository.the_record_exists(dataset, user_cookie)

    def create_new_record(self, dataset: DataSet, user_cookie: str) -> DSViewRecord:
        return self.repository.create_new_record(dataset, user_cookie)

    def create_cookie(self, dataset: DataSet) -> str:

        user_cookie = request.cookies.get("view_cookie")
        if not user_cookie:
            user_cookie = str(uuid.uuid4())

        existing_record = self.the_record_exists(
            dataset=dataset, user_cookie=user_cookie
        )

        if not existing_record:
            self.create_new_record(dataset=dataset, user_cookie=user_cookie)

        return user_cookie


class DOIMappingService(BaseService):
    def __init__(self):
        super().__init__(DOIMappingRepository())

    def get_new_doi(self, old_doi: str) -> str:
        doi_mapping = self.repository.get_new_doi(old_doi)
        if doi_mapping:
            return doi_mapping.dataset_doi_new
        else:
            return None


class SizeService:

    def __init__(self):
        pass

    def get_human_readable_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024**2:
            return f"{round(size / 1024, 2)} KB"
        elif size < 1024**3:
            return f"{round(size / (1024 ** 2), 2)} MB"
        else:
            return f"{round(size / (1024 ** 3), 2)} GB"
