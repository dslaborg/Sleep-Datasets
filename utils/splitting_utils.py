import logging

import pandas as pd

logger = logging.getLogger(__name__)


def extract_cfs_family_ids(meta_file):
    columns_of_interest = ["nsrrid", "familyi"]
    metadata = pd.read_csv(meta_file, usecols=columns_of_interest, dtype=str)
    metadata_dict = {}
    for _, row in metadata.iterrows():
        if row["nsrrid"] not in metadata_dict:
            metadata_dict[row["nsrrid"]] = row["familyi"]
        else:
            logger.info(f'Warning: {row["nsrrid"]} already in metadata_dict.')
    return metadata_dict
