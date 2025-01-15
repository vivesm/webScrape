
# Links to PDF Scraper

This project scrapes a website (help.okta.com website) collects all links from three levels of pages starting from a base URL, and saves each page as a PDF. The script uses a combination of `requests`, `BeautifulSoup` for scraping, and `Pyppeteer` for rendering pages as PDFs in a headless browser.

---

## 🎯 **Features**

- 🔗 Scrapes links from the `help.okta.com` domain.
- 🧭 Follows three levels of links starting from a base URL.
- 📄 Renders each page as a PDF using a headless browser (`Pyppeteer`).
- 📂 Saves PDFs in a specified directory.

---

## 🛠 **Prerequisites**

> **🖼 Canvas View: Prerequisites**  
> You need the following libraries installed to run the script:

```bash
pip install requests beautifulsoup4 pyppeteer
```

---

## 🚀 **Usage**

1. **Clone this repository** or download the script.
2. **Edit the script** if you need to change the base URL or output directory.
3. **Run the script**:

```bash
python script_name.py
```

---

### 📂 **Example**

```bash
$ python scraper.py
Rendering: https://help.okta.com/wf/en-us/content/topics/workflows/execute/flow-api-endpoint.htm
Saved PDF: js_rendered_pdfs/page_1.pdf
Rendering: https://help.okta.com/wf/en-us/content/topics/workflows/execute/flow-api-endpoint.htm#additional-topic
Saved PDF: js_rendered_pdfs/page_2.pdf
...
```

---

## 📦 **Directory Structure**

```
📂 js_rendered_pdfs
 ┣ 📜 page_1.pdf
 ┣ 📜 page_2.pdf
 ┗ 📜 ...
```

---

## 📑 **Functions**

> **🖼 Canvas View: Function Overview**  
>
> ### `get_links(url)`
> - **Purpose:** Fetches all links from the given URL.
> - **Filters:** Only includes links from the `help.okta.com` domain.
>
> ### `save_as_pdf(page_url, output_path)`
> - **Purpose:** Launches a headless browser using `Pyppeteer`.
> - **Functionality:** Renders the given URL as a PDF and saves it to the specified path.
>
> ### `scrape_3_levels()`
> - **Purpose:** 
>   - Scrapes links from the base URL, second-level links, and third-level links.
>   - Saves each collected page as a PDF in the output directory.

---

## 📜 **License**

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

---

## 💡 **Contributions**

For any issues or suggestions, feel free to open an issue or pull request.

---
