import sqlite3
import os
import csv
import shutil
import requests
import re
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("download_log.log"),  
        logging.StreamHandler()  
    ]
)

chrome_history_path = r""
temp_history_path = r""

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def is_direct_download_link(link):
    return ('file?h=' in link or 
            link.startswith('') or 
            '' in link or
            link.startswith(''))

def copy_chrome_history():
    if os.path.exists(chrome_history_path):
        shutil.copy2(chrome_history_path, temp_history_path)
        return True
    else:
        logging.error("This file does not exist. Please check if your path is correct and try again.")
        return False

def fetch_downloads():
    conn = sqlite3.connect(temp_history_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM downloads")
    downloads = cursor.fetchall()
    column_names = [description[0] for description in cursor.description]
    conn.close()
    return downloads, column_names

def save_downloads_to_csv(downloads, column_names):
    with open("downloads_history.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(column_names)
        writer.writerows(downloads)
    logging.info("Download history was successfully saved to 'downloads_history.csv'")

def download_file(link, output_dir, results_writer):
    try:
        response = requests.get(link)
        response.raise_for_status()

        if 'Content-Disposition' in response.headers:
            content_disposition = response.headers['Content-Disposition']
            match = re.search('filename="([^"]+)"', content_disposition)
            file_name = match.group(1) if match else link.split('/')[-1]
        else:
            file_name = link.split('/')[-1]

        sanitized_filename = sanitize_filename(file_name)
        if not sanitized_filename.endswith('.package'):
            sanitized_filename += '.package'

        filename = os.path.join(output_dir, sanitized_filename)
        with open(filename, 'wb') as f:
            f.write(response.content)

        logging.info(f"Download completed: {filename}")
        results_writer.writerow([link, "downloaded", sanitized_filename])
        return True

    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading {link}: {e}")
        results_writer.writerow([link, "failed", ""])
        return False

def process_downloads(downloads, column_names):
    output_dir = os.path.join(os.getcwd(), "customcreation")
    os.makedirs(output_dir, exist_ok=True)

    results_file_path = "download_results.csv"
    with open(results_file_path, mode="w", newline="", encoding="utf-8") as results_file:
        results_writer = csv.writer(results_file)
        results_writer.writerow(["link", "status", "filename"])

        total_links = 0
        downloaded_links = 0
        failed_links = 0
        non_direct_links = 0

        if 'tab_url' in column_names:
            urls_index = column_names.index('tab_url')
            links = [row[urls_index] for row in downloads if row[urls_index] is not None]

            logging.info(f"Total links found: {len(links)}")

            for index, link in enumerate(links, start=1):
                logging.debug(f"Processing link {index}/{len(links)}: {link}")
                total_links += 1

                if is_direct_download_link(link):
                    if download_file(link, output_dir, results_writer):
                        downloaded_links += 1
                    else:
                        failed_links += 1
                else:
                    logging.warning(f"The link {link} is not a direct file to download.")
                    results_writer.writerow([link, "is not a direct file to download", ""])
                    non_direct_links += 1

        logging.info("Report:")
        logging.info(f"Total files processed: {total_links}")
        logging.info(f"Files downloaded successfully: {downloaded_links}")
        logging.info(f"Download failures: {failed_links}")
        logging.info(f"Non-direct download links: {non_direct_links}")
        logging.info(f"Download results logged in '{results_file_path}'.")

def main():
    if copy_chrome_history():
        downloads, column_names = fetch_downloads()
        save_downloads_to_csv(downloads, column_names)
        process_downloads(downloads, column_names)
        os.remove(temp_history_path)

if __name__ == "__main__":
    main()
