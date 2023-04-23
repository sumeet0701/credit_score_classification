from collections import namedtuple


DataIngestionConfig = namedtuple("DataIngestionConfig",[
    "dataset_download_url",
    "raw_data_dir",
    "ingested_train_dir",
    "ingested_test_dir"])


DataValidationConfig = namedtuple("DataValidationConfig",[
    "schema_file_path",
    "report_file_path",
    "report_page_file_path"])

DataTransformationConfig = namedtuple("DataTransformationConfig",[
    "transformed_train_dir",
    "transformed_test_dir",
    "preprocessed_object_file_path",
    "feature_engineering_object_file_path"])

DatabaseConfig = namedtuple("DatabaseConfig",[
    "client_url",
    "database_name",
    "collection_name",
    "training_collection_name",
    "test_collection_name"])


TrainingPipelineConfig = namedtuple("TrainingPipelineConfig",["artifact_dir"])