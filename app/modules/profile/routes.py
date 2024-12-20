from app.modules.auth.services import AuthenticationService
from app.modules.auth.models import User
from app.modules.dataset.models import DataSet
from flask import render_template, redirect, url_for, request, abort
from flask_login import login_required, current_user

from app import db
from app.modules.profile import profile_bp
from app.modules.profile.forms import UserProfileForm
from app.modules.profile.services import UserProfileService
from app.modules.profile.models import UserProfile


@profile_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    auth_service = AuthenticationService()
    profile = auth_service.get_authenticated_user_profile()
    if not profile:
        return redirect(url_for("public.index"))

    form = UserProfileForm()
    if request.method == "POST":
        service = UserProfileService()
        result, errors = service.update_profile(profile.id, form)
        return service.handle_service_response(
            result,
            errors,
            "profile.edit_profile",
            "Profile updated successfully",
            "profile/edit.html",
            form,
        )

    return render_template("profile/edit.html", form=form)


@profile_bp.route("/profile/summary")
@login_required
def my_profile():
    page = request.args.get("page", 1, type=int)
    per_page = 5

    user_datasets_pagination = (
        db.session.query(DataSet)
        .filter(DataSet.user_id == current_user.id)
        .order_by(DataSet.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    total_datasets_count = (
        db.session.query(DataSet).filter(DataSet.user_id == current_user.id).count()
    )

    print(user_datasets_pagination.items)

    return render_template(
        "profile/summary.html",
        user_profile=current_user.profile,
        user=current_user,
        datasets=user_datasets_pagination.items,
        pagination=user_datasets_pagination,
        total_datasets=total_datasets_count,
    )


@profile_bp.route("/profile/<int:user_id>/datasets")
@login_required
def user_datasets(user_id):
    user = db.session.query(User).filter(User.id == user_id).first()

    if not user:
        abort(404)

    if user:
        page = request.args.get("page", 1, type=int)
        per_page = 5
        user_datasets_pagination = (
            db.session.query(DataSet)
            .filter(DataSet.user_id == user.id)
            .order_by(DataSet.created_at.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )

        total_datasets_count = (
            db.session.query(DataSet).filter(DataSet.user_id == user.id).count()
        )

        return render_template(
            "profile/user_datasets.html",
            user=user,
            datasets=user_datasets_pagination.items,
            pagination=user_datasets_pagination,
            total_datasets=total_datasets_count,
        )
    else:
        return redirect(url_for("public.index"))
