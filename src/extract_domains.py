from pathlib import Path

import pandas as pd


# Reads the raw Parquet dataset, normalizes the domain column, and writes the
# configured domain list file before returning the domains.
def extract_domains(raw_input_path: Path, output_path: Path) -> list[str]:

    if not raw_input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {raw_input_path}\n"
        )

    domains_table = pd.read_parquet(raw_input_path)

    DOMAIN_COLUMN = "root_domain"

    if DOMAIN_COLUMN not in domains_table.columns:
        raise ValueError(
            f"Column '{DOMAIN_COLUMN}' was not found in {raw_input_path}.\n"
        )

    # Normalize domains once at the input boundary so the crawler and detector
    # receive stable values no matter how the raw Parquet file was formatted.
    domains = domains_table[DOMAIN_COLUMN]
    domains = domains.dropna()
    domains = domains.astype(str)
    domains = domains.str.strip()
    domains = domains[domains != ""]
    domains = domains.str.lower()
    domains = domains.drop_duplicates()
    # Sorting makes repeated runs easier to compare.
    domains = domains.sort_values()
    domain_list = domains.tolist()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_text = "\n".join(domain_list) + "\n"

    output_path.write_text(output_text, encoding="utf-8")

    print(f"Input file: {raw_input_path}")
    print(f"Extracted domains: {len(domain_list)}")
    print(f"Output file: {output_path}")

    return domain_list

