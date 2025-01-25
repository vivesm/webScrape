# webScrape

BasicScraper is a Python-based web scraping tool that dynamically fetches web page links, downloads content as PDFs or text files, and handles cookie banners. The script uses Pyppeteer for headless browser automation and supports concurrency and delay configurations.

## Features

- Extracts links dynamically from a given URL.
- Saves content in **PDF** or **text** format.
- Handles cookie banners automatically (if supported).
- Skips re-downloading files that already exist.
- Configurable delays between processing each link.
- Test mode to process only the first link.

## Requirements

- Python 3.7+
- Virtual environment recommended.

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

Run the script with the desired options:

```bash
python webScrape.py.py --base_url <URL> [options]
```

### Command-Line Arguments

| Argument         | Description                                      | Default                                       |
|------------------|--------------------------------------------------|-----------------------------------------------|
| `--base_url`     | The URL to scrape links from.                   | `https://docs.workato.com/projects.html`     |
| `--output_format`| Output format for files (`pdf` or `text`).      | `pdf`                                        |
| `--test`         | Process only the first link (test mode).        | Disabled                                     |
| `--delay`        | Delay (in seconds) between processing links.    | `1.0`                                        |

### Example Usage

1. Scrape all links from a specific URL and save as PDFs:
   ```bash
   python webScrape.py.py --base_url https://docs.workato.com/getting-started/what-is-workato.html --output_format pdf
   ```

2. Test mode (process only the first link):
   ```bash
   python webScrape.py.py --test --base_url https://example.com
   ```

3. Add a 2-second delay between processing links:
   ```bash
   python webScrape.py.py --base_url https://example.com --delay 2
   ```

## Output

All files are saved in the `output/` directory. Files are named based on the last part of the URL, sanitized for safe filenames.

## Contributing

Contributions are welcome! Please fork the repository, make changes, and submit a pull request.

## License

This project is licensed under the MIT License.
