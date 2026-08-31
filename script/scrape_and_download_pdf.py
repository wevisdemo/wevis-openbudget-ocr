# /// script
# dependencies = [
#     "requests",
#     "selenium",
#     "pandas",
# ]
# ///
import os, json, re
import requests
from pathlib import Path
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_driver():
    """Configures and returns a Selenium WebDriver instance."""
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def download_pdf(pdf_url: str, out_dir:str|Path|None=None) -> None:
    response = requests.get(pdf_url)

    # Save the file locally
    filename = re.sub(r"(.*\/)", "", pdf_url)
    filename = re.sub(r"(?<=\.pdf).*", "", filename)
    if out_dir is None:
        out_dir = "/"
    output_path = os.path.join(out_dir, filename)
    with open(output_path, 'wb') as f:
        f.write(response.content)

    print(f'PDF saved to: {output_path}')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url", required=True, 
        help="URL to Budget Bureau pdf list page, for example: https://www.bb.go.th/topic3.php?catID=1538&gid=860&mid=544"
    )
    parser.add_argument("--pdf_out_dir", default="pdf", help="Path to output pdf files")
    
    args = parser.parse_args()
        
    URL = args.url
    PDF_OUT_PATH = args.pdf_out_dir
    
    os.makedirs(PDF_OUT_PATH, exist_ok=True)
    
    driver = setup_driver()
    
    try:
        doc_url = []
        # Navigate to the website
        for page in range(1, 3+1):
            
            url = URL + f"&page={page}"
            
            driver.get(url)
            
            # You can add more automation logic here
            images = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "img[data-original-title]"))
            )
            for img in images:
                # Check title
                title = img.get_attribute('data-original-title')
                if 'เอกสารงบประมาณ ฉบับที่ ๓' not in str(title):
                    continue
                
                doc_title = re.sub(r"(?<=พ\.ศ\.\s\d{4})(.*)", "", str(title))
                # Rearrange doc title
                doc_title = re.sub(
                    r"(เอกสาร.+?ฉบับที่\s\d)\s?(เล่มที่\s?\d(\s?\(\d\))?)\s?(งบประมาณ.+พ\.ศ\.\s?\d{4})",
                    r"\g<1> \g<4> \g<2>",
                    doc_title
                )
                
                parent = driver.execute_script("return arguments[0].parentNode;", img)
                doc_url.append({
                    'doc_title': doc_title,
                    'url': parent.get_attribute("href")
                })
        
        import time
        for doc in doc_url:
            driver.get(doc.get('url'))
            # Click download pdf
            _button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="a11y-landmark-content"]/div[5]/div[1]/div/div/div[2]/a'))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", _button)
            driver.execute_script("arguments[0].setAttribute('target', '_self');", _button)
            driver.execute_script("arguments[0].click();", _button)

            download_pdf(driver.current_url, out_dir=Path(PDF_OUT_PATH).resolve())
            doc['pdf_filename'] = re.sub(r".*\/", "", driver.current_url)
            time.sleep(0.5)
        
        index_output_path = os.path.join(PDF_OUT_PATH, 'doc_url_index.json')
        with open(index_output_path, 'w') as f:
            json.dump(doc_url, f, indent=4, ensure_ascii=False)
        
    except Exception as e:
        print(f"An error occurred: {e}")
        
    finally:
        # Ensure the browser closes even if an error occurs
        driver.quit()
        print("Driver closed.")
    

if __name__ == "__main__":
    main()