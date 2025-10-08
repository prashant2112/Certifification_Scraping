from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import csv
import os
import re
import unicodedata

# Setup Chrome
options = webdriver.ChromeOptions()
options.add_experimental_option("detach", True)
driver = webdriver.Chrome(options=options)

driver.get("https://learn.microsoft.com/en-us/credentials/browse/")

details = []
x = 1

while True:
    # Wait until cards load
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.grid-item"))
    )

    # Count how many cards are on the current page
    cards = driver.find_elements(By.CSS_SELECTOR, "li.grid-item")
    card_count = len(cards)

    for i in range(card_count):
        print(f"Processing card {x}")
        x += 1

        # Re-fetch fresh card (avoid stale element)
        cards = driver.find_elements(By.CSS_SELECTOR, "li.grid-item")
        card = cards[i]

        try:
            # Title and link
            data = card.find_element(By.CSS_SELECTOR, "a.card-title")
            Certificate_name = data.text.strip()
            link = data.get_attribute("href")

            Vendor = "Microsoft"

            # Level
            meta_items = card.find_elements(By.CSS_SELECTOR, "ul.metadata.page-metadata.font-size-xs li")
            Level = meta_items[2].text.strip() if len(meta_items) >= 3 else "N/A"

            # Exam code
            if ":" in Certificate_name:
                Full = Certificate_name.split(":", 1)
                Exam_Code = Full[0].strip()
                Certification_Name = Full[1].strip()
            else:
                Exam_Code = "N/A"
                Certification_Name = Certificate_name

            # Go to detail page
            driver.get(link)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.content"))
            )
            dsoup = BeautifulSoup(driver.page_source, "html.parser")

            # Learning path
            learning_path_elements = dsoup.select("ul#learning-paths-list li a.card-title")
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul#learning-paths-list li a.card-title"))
                )
                dsoup = BeautifulSoup(driver.page_source, "html.parser")

                learning_path_elements = dsoup.select("ul#learning-paths-list li a.card-title")
                learning_paths = [lp.get_text(strip=True) for lp in learning_path_elements]

                Learning_path = ""
                for i, title in enumerate(learning_paths, 1):
                    path= f" Module {i}. {title}. "
                    paths = path.strip()
                    Learning_path = Learning_path + " " +paths
                
            except Exception as e:
                
                learning_paths = "[N/A]"
            # Overview + Objective
            summary = dsoup.find("div", class_="content")
            overview, objective = "", ""
            if summary:
                paragraphs = summary.find_all("p")
                clean_paragraphs = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text.startswith("Warning") or "This exam retired" in text:
                        continue
                    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
                    text = re.sub(r"[^A-Za-z0-9 .,!?':;()-]+", '', text)
                    if text:
                        clean_paragraphs.append(text)
                if clean_paragraphs:
                    overview = clean_paragraphs[0]
                    objective = " ".join(clean_paragraphs)

            # Save row
            details.append([Exam_Code, Certification_Name, Vendor, Level, overview, objective, Learning_path])

            # Back to list
            driver.back()
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.grid-item"))
            )

        except Exception as e:
            print(f"⚠️ Error processing card {x-1}: {e}")
            driver.back()
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.grid-item"))
            )
            continue

    # --- Hardcoded Pagination ---
    try:
        wait = WebDriverWait(driver, 5)
        # This XPath points to the "Next" button at the bottom right
        next_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="content-browser-container"]/div/div/div[2]/div[4]/div[1]/div/nav/ul/li[last()]/button')
        ))
        if "disabled" in next_btn.get_attribute("class"):
            print("✅ Reached last page.")
            break
        driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
        time.sleep(1)
        next_btn.click()
        time.sleep(2)
    except:
        print("✅ No more pages.")
        break

driver.quit()

# Save CSV
file_name = "certification_details.csv"
with open(file_name, "w", newline="", encoding="utf-8-sig") as file:
    writer = csv.writer(file)
    writer.writerow(["Exam_Code", "Certification_Name", "Vendor", "Level", "Overview", "Objective", "Learning_Path"])
    writer.writerows(details)

print(f"🎉 Done! {len(details)} certifications saved into {file_name}")
