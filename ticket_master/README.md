# Ticketmaster Event Downloader

Fetch events from the Ticketmaster Discovery API, filter them by time, location, or keyword, and export the results to a CSV file.

## How to Use

1. Open `run.py` and edit the `config` dictionary, including the API key, time range, city, and other filters.
2. Run:

```bash
python run.py
```

3. The results will be written to the CSV file specified by `config["out"]`. The default output file is `events.csv`.

This project uses only the Python standard library, so no additional packages are required.

## Configuration Options

| Key | Description | Required |
|------|-------------|----------|
| `apikey` | Ticketmaster API key ([apply for a free key](https://developer.ticketmaster.com)) | Yes |
| `start_time` / `end_time` | Time range in UTC format: `2026-04-10T00:00:00Z` | No |
| `city` | City name | No |
| `country_code` | Country code, such as `US`, `GB`, or `PK` | No |
| `keyword` | Keyword used to search for events | No |
| `out` | Output CSV filename | No, defaults to `events.csv` |
| `size` | Number of events per page, up to 200 | No, defaults to 100 |
| `max_pages` | Maximum number of result pages to fetch | No, defaults to 5 |

Options that are not needed can be removed or left empty.

## Project Files

- `run.py` — Edit the `config` dictionary in this file, then run it.
- `ticketmaster_download.py` — Contains the main logic. The `download(config)` function fetches events, transforms the data, and writes the results to a CSV file.

## CSV Columns

```text
name, description, location_name, latitude, longitude, address,
start_time, end_time, city, primary_category, secondary_categories,
thumbnail_image, additional_images, external_link, is_paid
```
