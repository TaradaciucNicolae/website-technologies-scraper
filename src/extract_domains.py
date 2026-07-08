
from pathlib import Path
# A Parquet file is basically a table, so pandas is a convenient tool here.
import pandas as pd


def extract_domains(raw_input_path: Path, output_path: Path) -> list[str]:

    if not raw_input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {raw_input_path}\n"
        )

    domains_table = pd.read_parquet(raw_input_path)

    # Print basic information about the dataset
    print("Available columns:", list(domains_table.columns))
    print("Preview:")
    print(domains_table.head())

    # The uploaded dataset has a column called  "root_domain"
    # That column contains the domains
    DOMAIN_COLUMN = "root_domain"

    # Check that the expected column exists
    if DOMAIN_COLUMN not in domains_table.columns:
        raise ValueError(
            f"Column '{DOMAIN_COLUMN}' was not found in {raw_input_path}.\n"
        )

    # Selecting the domain column
    domains = domains_table[DOMAIN_COLUMN]

    # This removes empty lines
    domains = domains.dropna()

    # Convert all values to strings
    domains = domains.astype(str)

    # str.strip() removes spaces from the beginning and end -> It removes the extra whitespace.
    domains = domains.str.strip()

    # Remove empty strings after trimming
    domains = domains[domains != ""]

    # Normalize domains to lowercase
    domains = domains.str.lower()

    domains = domains.drop_duplicates()

    domains = domains.sort_values()

    # Convert the domain list to a Python list for easier writing to a text file
    domain_list = domains.tolist()

    # Make sure the output folder exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write domains to the output file
    output_text = "\n".join(domain_list) + "\n"

    output_path.write_text(output_text, encoding="utf-8")


    # Summary:
    print(f"Input file: {raw_input_path}")
    print(f"Extracted domains: {len(domain_list)}")
    print(f"Output file: {output_path}")

    return domain_list

