# Generated by Selenium IDE
import pytest
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

class TestTest():
  def setup_method(self, method):
    self.driver = webdriver.Chrome()
    self.vars = {}
  
  def teardown_method(self, method):
    self.driver.quit()
  
  def test_test(self):
    self.driver.get("http://127.0.0.1:5000/")
    self.driver.set_window_size(912, 1028)
    self.driver.find_element(By.LINK_TEXT, "Sample dataset 4").click()
    self.driver.find_element(By.CSS_SELECTOR, ".nav-link:nth-child(2)").click()
    self.driver.find_element(By.ID, "email").click()
    self.driver.find_element(By.ID, "email").send_keys("user2@example.com")
    self.driver.find_element(By.ID, "password").click()
    self.driver.find_element(By.ID, "password").send_keys("1234")
    self.driver.find_element(By.ID, "submit").click()
    self.driver.find_element(By.LINK_TEXT, "Sample dataset 4").click()

    # Esperar a que el elemento sea clickeable
    edit_button = WebDriverWait(self.driver, 10).until(
      expected_conditions.element_to_be_clickable((By.ID, "edit35"))
    )
    
    # Desplazarse al boton de editar
    self.driver.execute_script("arguments[0].scrollIntoView();", edit_button)
    
    # Intentar hacer clic en el botón de editar usando JavaScript
    self.driver.execute_script("arguments[0].click();", edit_button)
    
    # Esperar un momento para ver el resultado
    time.sleep(1)
    
    self.driver.find_element(By.ID, "fileContentEdit").click()
    element = self.driver.find_element(By.ID, "fileContentEdit")
    self.driver.execute_script("if(arguments[0].contentEditable === 'true') {arguments[0].innerText = 'features\\n    Chat\\n        mandatory\\n            Connection\\n                alternative\\n                  EDITADO EN SELENIUM\\n                or\\n                    Text\\n                    Video\\n                    Audio\\n        optional\\n            \"Data Storage\"\\n            \"Media Player\"\\n\\nconstraints\\n    Server =&gt; \"Data Storage\"\\n    Video | Audio =&gt; \"Media Player\"\\n'}", element)
    save_button = WebDriverWait(self.driver, 10).until(
      expected_conditions.element_to_be_clickable((By.ID, "save"))
      )
    
    # Desplazarse al boton de guardar
    self.driver.execute_script("arguments[0].scrollIntoView();", save_button)
    
    # Intentar hacer clic en el botón de guardar usando JavaScript
    self.driver.execute_script("arguments[0].click();", save_button)
    
    time.sleep(4)
    assert self.driver.switch_to.alert.text == "File saved successfully"