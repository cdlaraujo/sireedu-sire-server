# Tools Scripts for SIREEDU Survey

## Import Educational Products from Excel file

This script imports educational products from an Excel file. For now, it only accepts the excel file named [`SIREEDU-V3.xlsx`](https://docs.google.com/spreadsheets/d/1is57VLOGSSCK_Qyzh2jRMnN-DTkK2Pxg/edit?usp=sharing&ouid=104422702713682419880&rtpof=true&sd=true) and the sheet named `Matriz`. The script will create a new educational product for each row in the sheet.

> [!IMPORTANT]
> The Excel file is private and can only be accessed by the project members. If you need access to the file, please contact Prof. Lucineide.

### Requirements

- Python 3.11 (The same version used in the project)
- Install the project dependencies by running `pip install -r requirements.txt` in the project root directory.
- Install the tools dependencies by running `pip install -r sisen/survey/tools/requirements.txt`.

### Usage

```bash
python -m sisen.survey.tools.import_data -f excel_file.xlsx [-s sheet_name]
```

| Argument | Description                                                         |
| -------- | ------------------------------------------------------------------- |
| -f       | The Excel file to import the data from.                             |
| -s       | The name of the sheet to import the data from. Default is `Matriz`. |
