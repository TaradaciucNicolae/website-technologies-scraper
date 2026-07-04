
from pathlib import Path
# A Parquet file is basically a table, so pandas is a convenient tool here.
import pandas as pd

RAW_INPUT_PATH = Path("data/raw/domains.snappy.parquet")
OUTPUT_PATH = Path("data/domains.txt")

def main() -> None:

    if not RAW_INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found: {RAW_INPUT_PATH}\n"
        )
    
    domains_table = pd.read_parquet(RAW_INPUT_PATH)

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
            f"Column '{DOMAIN_COLUMN}' was not found in {RAW_INPUT_PATH}.\n"
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
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Write domains to the output file
    output_text = "\n".join(domain_list) + "\n"

    OUTPUT_PATH.write_text(output_text, encoding="utf-8")


    # Summary:
    print(f"Input file: {RAW_INPUT_PATH}")
    print(f"Extracted domains: {len(domain_list)}")
    print(f"Output file: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()