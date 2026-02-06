import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import csv
from dotenv import load_dotenv
import os

load_dotenv()

email = os.getenv("PIAZZA_EMAIL")
password = os.getenv("PIAZZA_PASSWORD")

all_posts = {}

def get_i_answer():
    try:
        answer_box = driver.find_element(By.CSS_SELECTOR, '[data-id="i_answer"]')
        inner_div = answer_box.find_element(By.CLASS_NAME, "history-selection")
        text = inner_div.text.strip()
        return text
    except NoSuchElementException:
        return None

def search_folder(folder_button):
    post_links = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "feed-item-wrapper")))
    print(f"✅ Found {len(post_links)} posts.")
    data = []
    for i in range(len(post_links)):
        post = post_links[i]

        try:
            driver.execute_script("arguments[0].click();", post)
            
            # Wait for content to load
            content = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-id='renderHtmlId']")))

            text = content.text

            full_post = "Question: " + text
            full_post += "\nAnswer: " + get_i_answer() if get_i_answer() else ""

            data.append(full_post)

            time.sleep(1)

        except Exception as e:
            print(f"❌ Error on post {i}: {e}")
    all_posts[folder_button.text] = data

driver = webdriver.Chrome()
driver.get("https://piazza.com/")

wait = WebDriverWait(driver, timeout=10)
login_button = wait.until(EC.presence_of_element_located((By.ID, "login_button")))
login_button.click()

email_input = wait.until(EC.visibility_of_element_located((By.NAME, "email")))
email_input.send_keys(email)

password_input = driver.find_element(By.NAME, "password")
password_input.send_keys(password)

submit_btn = driver.find_element(By.ID, "modal_login_button")
submit_btn.click()
time.sleep(0.2)

current_url = driver.current_url
if "class" in current_url:
    print("✅ Login successful! Redirected to:", current_url)
else:
    print("❌ Login might have failed. Current URL:", current_url)

driver.fullscreen_window()

folder_buttons = wait.until(
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[id^='topbar_folder_']"))
)

print(f"✅ Found {len(folder_buttons)} folders.")

for folder_button in folder_buttons:
    try:
        folder_name = folder_button.text
        folder_button.click()
        time.sleep(2)
        print(f"Searching in {folder_name}...")
        search_folder(folder_button)
    except Exception as e:
        print(f"❌ Error searching in {folder_name}: {e}")

with open("piazza_posts.csv", "a", newline='', encoding="utf-8") as file:
    writer = csv.writer(file)
    for folder, posts in all_posts.items():
        for post in posts:
            writer.writerow([folder, post])

# for folder_button in folder_buttons:
#     try:
#         folder_name = folder_button.text
#         print(f"Searching in {folder_name}...")
#         search_folder(driver, folder_button)
#     except Exception as e:
#         print(f"❌ Error searching in {folder_name}: {e}")

# print(all_posts)


# driver.quit()