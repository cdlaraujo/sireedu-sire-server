import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sisen.settings")
django.setup()

import pandas as pd
from abc import ABC, abstractmethod
import enum
from colorama import Fore, Style
import argparse
from typing import List, Dict, Any

from sisen.survey.models import (
    EducationalType,
    EducationalProduct,
    StudyOption,
    Study,
)


class ImportData(ABC):
    class ImportError(Exception):
        def __init__(self, error_type, details=None):
            self.error_type = error_type
            self.details = details
            super().__init__(f"{error_type.value}: {details}" if details else error_type.value)

    class ErrorType(enum.Enum):
        PRODUCT_TYPE_NOT_FOUND = "Product type not found"
        PRODUCT_ALREADY_EXISTS = "Product already exists"
        STYLE_NOT_FOUND = "Style not found"
        INTELLIGENCE_NOT_FOUND = "Intelligence not found"
        LINE_NOT_VALID = "Line not valid - missing required fields"
        COLUMN_MAPPING_ERROR = "Column mapping error" # New error type
        FILE_READ_ERROR = "File read error" # New error type
        SUCCESS = "Success"

    def __init__(self, file_path: str):
        self.file_path = file_path

    def import_data(self, **kargs):
        try:
            raw_data = self._read_file(**kargs)
            normalized_data = self._normalize_columns(raw_data)
        except (FileNotFoundError, ValueError, self.ImportError) as e:
            print(f"{Fore.RED}Failed to prepare data: {e}{Style.RESET_ALL}")
            return # Stop if file reading or normalization fails

        success_count = 0
        error_count = 0

        for index, row in normalized_data.iterrows():
            # Use 0-based index for user feedback, matching pandas default
            excel_row_index = index + normalized_data.attrs.get('header_row_index', 0) + 2 # +2 for header and 1-based excel index
            try:
                self._process_row(row)
                success_count += 1
                print(
                    f"{Fore.GREEN}Excel Row {excel_row_index}: Successfully imported{Style.RESET_ALL}"
                )
            except self.ImportError as e:
                error_count += 1
                self._print_error(e, excel_row_index, row)
            except Exception as e: # Catch unexpected errors during row processing
                error_count += 1
                print(f"{Fore.RED}Unexpected error processing Excel row {excel_row_index}: {e}{Style.RESET_ALL}")
                self._print_error(self.ImportError(self.ErrorType.LINE_NOT_VALID, f"Unexpected error: {e}"), excel_row_index, row)


        print(f"\n{Fore.CYAN}Import summary:{Style.RESET_ALL}")
        print(f"Total rows processed: {success_count + error_count}")
        print(f"{Fore.GREEN}Successfully imported: {success_count}{Style.RESET_ALL}")
        if error_count > 0:
            print(f"{Fore.RED}Errors: {error_count}{Style.RESET_ALL}")

    def _print_error(self, error, excel_row_index, row=None):
        """Print detailed error information with context"""
        print(f"{Fore.RED}Error in Excel row {excel_row_index}:{Style.RESET_ALL}")
        print(f"  Error type: {error.error_type.value}")

        if error.details:
            print(f"  Details: {error.details}")

        # Attempt to print some identifying info from the row if available and normalized
        if row is not None and isinstance(row, pd.Series):
            try:
                product_name = row.get('product_name', 'N/A')
                code = row.get('educational_code', 'N/A')
                print(f"  Product Name (from data): {product_name}")
                print(f"  Code (from data): {code}")
            except Exception:
                 # If accessing row data fails, just continue
                 pass

        print("")

    @abstractmethod
    def _read_file(self, **kargs) -> pd.DataFrame:
        """Reads the file and returns a raw DataFrame."""
        pass

    @abstractmethod
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Renames columns to a standard internal format."""
        pass

    @abstractmethod
    def _process_row(self, row: pd.Series):
        """Process one data row (Series) with normalized columns, raise ImportError for any issues"""
        pass


class ImportProductsFromExcel(ImportData):

    # Define internal standard names for columns
    INTERNAL_COLUMNS = {
        'product_name': True, # True indicates required
        'description': True,
        'link': True,
        'product_type': True,
        'styles_raw': True,
        'intelligences_raw': True,
        'activity_type': False, # False indicates optional
        'media_format': False,
        'content_source': False,
        'educational_code': False,
    }

    # Map internal names to lists of possible Excel header names
    COLUMN_NAME_MAPPING = {
        'product_name': ['Nome do Software', 'Nome da Plataforma', 'Product Name', 'Software'],
        'description': ['Descrição', 'Description', 'Info'],
        'link': ['Link de Acesso', 'Link', 'URL', 'Access Link'],
        'product_type': ['Tipo de Produto Educacional', 'Product Type', 'Tipo'],
        'styles_raw': ['Perfis de EA (quando possível, listar mais de um perfil)', 'EA', 'Estilos Aprendizagem', 'Learning Styles'],
        'intelligences_raw': ['Perfis de IM (quando possível, listar mais de um perfil)', 'IM', 'Inteligências Múltiplas', 'Multiple Intelligences'],
        'activity_type': ['Tipo de OE', 'Activity Type', 'OE Type'],
        'media_format': ['Formato de OE', 'Media Format', 'OE Format'],
        'content_source': ['Plataforma', 'Source', 'Content Source', 'Platform'],
        'educational_code': ['Código', 'Code', 'Educational Code', 'ID'],
    }

    # --- Mappings for data values ---
    PRODUCT_TYPES_EXCEL_TO_DB = {
        "Tutoriais": "Tutoriais",
        "Vídeos": "Vídeos",
        "Exercitação": "Exercitação",
        "Software Educacional": "Software Educacional",
    }

    STYLES_EXCEL_TO_DB = {
        "Ativo": "Ativo",
        "Reflexivo": "Reflexivo",
        "Pragmático": "Pragmático",
        "Teórico": "Teórico",
    }

    INTELLIGENCES_EXCEL_TO_DB = {
        "Linguística": "Verbal Linguística",
        "Lógico-Matemática": "Lógica Matemática",
        "Espacial": "Visual Espacial",
        "Interpessoal": "Interpessoal",
        "Cinestésica": "Cinestésica Corporal",
        "Intrapessoal": "Intrapessoal",
    }
    # --- End Mappings ---

    def _read_file(self, **kargs) -> pd.DataFrame:
        """Reads the Excel file, finds the header, and returns the data."""
        try:
            # Read without header first to find the actual header row
            df_peek = pd.read_excel(self.file_path, header=None, **kargs)
            header_row_index = 0
            for index, row in df_peek.iterrows():
                # Simple check: assume header is the first row with likely column names
                # This heuristic might need adjustment based on file patterns
                # Check if at least N values look like potential headers (non-empty strings)
                potential_headers = [str(x) for x in row if pd.notna(x) and isinstance(x, str) and x.strip()]
                if len(potential_headers) > 3: # Adjust threshold as needed
                    header_row_index = index
                    break
            else:
                # If no suitable header row found after checking all rows
                 raise self.ImportError(self.ErrorType.FILE_READ_ERROR, "Could not automatically determine the header row.")


            # Read the file again, using the determined header row
            data = pd.read_excel(self.file_path, header=header_row_index, **kargs)
            # Store the header row index for accurate error reporting later
            data.attrs['header_row_index'] = header_row_index
            return data
        except FileNotFoundError:
            raise self.ImportError(self.ErrorType.FILE_READ_ERROR, f"File not found at {self.file_path}")
        except Exception as e: # Catch other potential pandas errors
            raise self.ImportError(self.ErrorType.FILE_READ_ERROR, f"Error reading Excel file: {e}")


    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Renames DataFrame columns based on COLUMN_NAME_MAPPING."""
        rename_map: Dict[str, str] = {}
        found_internal_names = set()
        original_columns = list(df.columns) # Work with a copy

        for internal_name, possible_names in self.COLUMN_NAME_MAPPING.items():
            found_match = None
            for possible_name in possible_names:
                # Case-insensitive matching, stripping whitespace
                match = next((col for col in original_columns if isinstance(col, str) and col.strip().lower() == possible_name.strip().lower()), None)
                if match:
                    if found_match:
                        # Avoid mapping multiple Excel columns to the same internal name
                        raise self.ImportError(
                            self.ErrorType.COLUMN_MAPPING_ERROR,
                            f"Multiple columns ('{found_match}', '{match}') found mapping to internal name '{internal_name}'. Please check Excel headers."
                        )
                    found_match = match
                    # Remove the matched column to prevent it from matching another internal name
                    original_columns.remove(match)

            if found_match:
                rename_map[found_match] = internal_name
                found_internal_names.add(internal_name)
            elif self.INTERNAL_COLUMNS[internal_name]: # Check if the column was required
                raise self.ImportError(
                    self.ErrorType.COLUMN_MAPPING_ERROR,
                    f"Required column for '{internal_name}' not found. Expected one of: {possible_names}"
                )

        # Check if all required internal columns were found
        required_internal = {k for k, v in self.INTERNAL_COLUMNS.items() if v}
        missing_required = required_internal - found_internal_names
        if missing_required:
             raise self.ImportError(
                self.ErrorType.COLUMN_MAPPING_ERROR,
                f"Missing required columns: {', '.join(missing_required)}. Check Excel headers and mapping."
            )

        df.rename(columns=rename_map, inplace=True)

        # Keep only the columns that were successfully mapped to internal names
        final_columns = [col for col in df.columns if col in self.INTERNAL_COLUMNS]
        return df[final_columns]


    def _process_row(self, row: pd.Series):
        """Processes a single row with normalized column names."""
        # --- Extract data using internal names ---
        product_name = str(row["product_name"]).strip().strip(".")
        description = str(row["description"]).strip().strip(".")
        link = str(row["link"]).strip().strip(".")
        product_type = str(row["product_type"]).strip()

        # Split comma-separated styles and intelligences, handle potential NaN/empty strings
        styles_str = str(row["styles_raw"]) if pd.notna(row["styles_raw"]) else ""
        intelligences_str = str(row["intelligences_raw"]) if pd.notna(row["intelligences_raw"]) else ""

        product_styles_raw = [s.strip() for s in styles_str.split(',') if s.strip()]
        product_intelligences_raw = [i.strip() for i in intelligences_str.split(',') if i.strip()]

        # Optional fields: Use .get() with default to handle missing columns gracefully
        activity_type = str(row.get("activity_type", "")).strip() if pd.notna(row.get("activity_type")) else ""
        media_format = str(row.get("media_format", "")).strip() if pd.notna(row.get("media_format")) else ""
        content_source = str(row.get("content_source", "")).strip() if pd.notna(row.get("content_source")) else ""
        educational_code = str(row.get("educational_code", "")).strip() if pd.notna(row.get("educational_code")) else ""

        # --- Basic validation for essential fields ---
        # Check required string fields
        if not all([product_name, description, link, product_type]):
             missing = [name for name, val in [('Name', product_name), ('Description', description), ('Link', link), ('Type', product_type)] if not val]
             raise self.ImportError(
                self.ErrorType.LINE_NOT_VALID,
                f"Missing required text fields: {', '.join(missing)}"
            )
        # Check required list fields (styles/intelligences)
        if not product_styles_raw or not product_intelligences_raw:
             missing_lists = []
             if not product_styles_raw: missing_lists.append("Style (EA)")
             if not product_intelligences_raw: missing_lists.append("Intelligence (IM)")
             raise self.ImportError(
                self.ErrorType.LINE_NOT_VALID,
                f"Missing required classifications: {', '.join(missing_lists)} cannot be empty."
            )

        # --- Data processing and validation ---
        # Truncate description
        description = description[:250] + "..." if len(description) > 250 else description

        # Validate and map product type
        product_type_str = self.PRODUCT_TYPES_EXCEL_TO_DB.get(product_type)
        if not product_type_str:
            raise self.ImportError(
                self.ErrorType.PRODUCT_TYPE_NOT_FOUND,
                f"Unknown type: '{product_type}'. Valid types: {', '.join(self.PRODUCT_TYPES_EXCEL_TO_DB.keys())}",
            )
        try:
            product_type_obj = EducationalType.objects.get(name=product_type_str)
        except EducationalType.DoesNotExist:
             raise self.ImportError(
                self.ErrorType.PRODUCT_TYPE_NOT_FOUND,
                f"Product type '{product_type_str}' not found in database",
            )

        # Validate and map styles
        style_dbs = self._validate_and_map_study_options(
            product_styles_raw, self.STYLES_EXCEL_TO_DB, "EA", self.ErrorType.STYLE_NOT_FOUND, "style"
        )

        # Validate and map intelligences
        intelligence_dbs = self._validate_and_map_study_options(
            product_intelligences_raw, self.INTELLIGENCES_EXCEL_TO_DB, "IM", self.ErrorType.INTELLIGENCE_NOT_FOUND, "intelligence"
        )

        # --- Database operation (Update or Create) ---
        # Use update_or_create for atomicity and simplicity
        product, created = EducationalProduct.objects.update_or_create(
            link=link, # Using link as the primary lookup key
            name=product_name, # Add name to make the lookup more specific if needed
            defaults={
                'info': description,
                'type': product_type_obj,
                'content_source': content_source,
                'activity_type': activity_type,
                'media_format': media_format,
                'educational_code': educational_code,
            }
        )

        # Update ManyToMany fields separately after create/update
        product.styles.set(style_dbs)
        product.intelligences.set(intelligence_dbs)

        # action = "Created" if created else "Updated"
        # print(f"  {action} product: {product_name} ({educational_code or 'No Code'})")


    def _validate_and_map_study_options(
        self, raw_options: List[str], mapping: Dict[str, str], study_acronym: str, error_type: ImportData.ErrorType, option_name: str
    ) -> List[StudyOption]:
        """Helper to validate and map styles or intelligences."""
        option_objects = []
        try:
            study = Study.objects.get(acronym=study_acronym)
        except Study.DoesNotExist:
             # This should ideally not happen if DB is set up correctly
             raise self.ImportError(error_type, f"Study '{study_acronym}' not found in database.")

        for raw_option in raw_options:
            db_name = mapping.get(raw_option)
            if not db_name:
                raise self.ImportError(
                    error_type,
                    f"Unknown {option_name} in Excel: '{raw_option}'. Valid {option_name}s: {', '.join(mapping.keys())}",
                )
            try:
                option_obj = StudyOption.objects.get(study=study, description=db_name)
                option_objects.append(option_obj)
            except StudyOption.DoesNotExist:
                raise self.ImportError(
                    error_type, f"{option_name.capitalize()} '{db_name}' not found in database for study {study_acronym}"
                )
        return option_objects


def main():
    parser = argparse.ArgumentParser(description="Import educational products from Excel file")
    parser.add_argument(
        "--file_path", "-f", type=str, required=True, help="Path to the Excel file with the data"
    )
    parser.add_argument(
        "--sheet_name",
        "-s",
        type=str,
        help="Name or index (0-based) of the sheet in the Excel file to import. Defaults to the first sheet.",
        default=0, # Default to first sheet by index
    )

    args = parser.parse_args()
    import_data_task = ImportProductsFromExcel(args.file_path)
    import_data_task.import_data(sheet_name=args.sheet_name)


if __name__ == "__main__":
    main()