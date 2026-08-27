import logging
import os
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import h5py
import hydra
import numpy as np
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, OmegaConf
from psg_utils import Defaults
from psg_utils.dataset import SleepStudyDataset

logger = logging.getLogger(__name__)
logging.captureWarnings(True)


def setup_default_sleep_stages(sleep_stage_dict):
    Defaults.AWAKE[1] = sleep_stage_dict[Defaults.AWAKE[0]]
    Defaults.NON_REM_STAGE_1[1] = sleep_stage_dict[Defaults.NON_REM_STAGE_1[0]]
    Defaults.NON_REM_STAGE_2[1] = sleep_stage_dict[Defaults.NON_REM_STAGE_2[0]]
    Defaults.NON_REM_STAGE_3[1] = sleep_stage_dict[Defaults.NON_REM_STAGE_3[0]]
    Defaults.REM[1] = sleep_stage_dict[Defaults.REM[0]]
    Defaults.UNKNOWN[1] = sleep_stage_dict[Defaults.UNKNOWN[0]]


def preprocess_study(h5_file_group, study):
    logger.info(f"processing recording {study.identifier}")
    # Create groups
    study_group = h5_file_group.create_group(study.identifier)
    psg_group = study_group.create_group("PSG")
    with study.loaded_in_context(allow_missing_channels=True):
        X, y = study.get_all_periods()
        for chan_ind, channel_name in enumerate(study.select_channels):
            assert (
                channel_name.original_name in h5_file_group.attrs["eeg_channels"]
                or channel_name.original_name in h5_file_group.attrs["eog_channels"]
                or channel_name.original_name in h5_file_group.attrs["emg_channels"]
            ), f"Channel {channel_name.original_name} not in eeg_channels or eog_channels or emg_channels"
            # Create PSG channel datasets
            psg_group.create_dataset(
                channel_name.original_name, data=X[..., chan_ind].ravel()
            )
        # Create hypnogram dataset
        study_group.create_dataset("hypnogram", data=y)

        # Create class --> index lookup groups
        cls_to_indx_group = study_group.create_group("class_to_index")
        dtype = np.dtype("uint16") if len(y) <= 65535 else np.dtype("uint32")
        classes = study.hypnogram.classes
        for class_ in classes:
            inds = np.where(y == class_)[0].astype(dtype)
            cls_to_indx_group.create_dataset(str(class_), data=inds)

        # Set attributes, currently only sample rate is (/may be) used
        study_group.attrs["sample_rate"] = study.sample_rate


def set_preprocessing_pipeline(
    dataset, sample_rate, strip_settings, filter_settings, quality_settings, scaler
):
    dataset.set_sample_rate(sample_rate)

    # Apply strip function if specified
    dataset.set_strip_func(**strip_settings)

    # Set filtering
    dataset.set_filter_settings(**filter_settings)

    # Apply quality control function if specified
    dataset.set_quality_control_func(**quality_settings)

    # Set scaler
    dataset.set_scaler(scaler)


@hydra.main(config_path="./config", version_base="1.2", config_name="preprocess")
def main(cfg: DictConfig):
    hydra_cfg = HydraConfig.get()
    logger.info(f"overrides:\n{OmegaConf.to_yaml(hydra_cfg.overrides)}")

    setup_default_sleep_stages(cfg.general.rstages)

    save_file = os.path.abspath(cfg.save_file)

    if os.path.exists(save_file):
        raise ValueError(f"Out file at {save_file} already exists")

    out_dir = os.path.split(save_file)[0]
    os.makedirs(out_dir, exist_ok=True)

    with ThreadPoolExecutor(cfg.num_threads) as pool:
        with h5py.File(save_file, "w") as h5_file:
            for dataset in cfg.datasets:
                dataset_cfg = cfg.datasets[dataset]
                # Process each dataset
                dataset_name = dataset_cfg.name

                # create group for dataset
                h5_dataset_group = h5_file.create_group(dataset_name)
                h5_dataset_group.attrs["eeg_channels"] = list(
                    dataset_cfg.psg.eeg_channels
                    if dataset_cfg.psg.renamed_eeg_channels is False
                    else dataset_cfg.psg.renamed_eeg_channels
                )
                h5_dataset_group.attrs["eog_channels"] = list(
                    dataset_cfg.psg.eog_channels
                    if dataset_cfg.psg.renamed_eog_channels is False
                    else dataset_cfg.psg.renamed_eog_channels
                )
                h5_dataset_group.attrs["emg_channels"] = list(
                    dataset_cfg.psg.emg_channels
                    if dataset_cfg.psg.renamed_emg_channels is False
                    else dataset_cfg.psg.renamed_emg_channels
                )

                # Run the preprocessing
                process_func = partial(preprocess_study, h5_dataset_group)

                data_dir = os.path.join(cfg.general.save_dir, dataset_name)

                # include everything in folder_regex but the folders in bad_recordings
                bad_recordings = dataset_cfg.bad_recordings
                folder_regex = ".+"
                for bad_recording in bad_recordings:
                    folder_regex = folder_regex + f"(?<!{bad_recording})"
                folder_regex = folder_regex + "$"

                dataset = SleepStudyDataset(
                    data_dir=data_dir,
                    folder_regex=folder_regex,
                    psg_regex=dataset_cfg.preprocessing.psg_regex,
                    hyp_regex=dataset_cfg.preprocessing.hyp_regex,
                    period_length=cfg.general.epoch_duration,
                    on_overlapping="RAISE",
                    annotation_dict=None,
                    identifier=dataset_name,
                )
                set_preprocessing_pipeline(
                    dataset,
                    sample_rate=cfg.general.sample_rate,
                    strip_settings=cfg.strip_func,
                    filter_settings=OmegaConf.to_container(cfg.filter_settings),
                    quality_settings=cfg.quality_control_func,
                    scaler=cfg.scaler,
                )

                logger.info(f"Preprocessing dataset: {dataset_name}")
                n_pairs = len(dataset.pairs)
                for i, _ in enumerate(pool.map(process_func, dataset.pairs)):
                    print(f"finished recording {i+1}/{n_pairs}")
                logger.info("")


if __name__ == "__main__":
    main()
