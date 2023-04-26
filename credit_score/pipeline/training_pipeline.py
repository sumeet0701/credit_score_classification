from collections import namedtuple
from datetime import datetime
import uuid
from threading import Thread
from typing import List
from multiprocessing import Process
from credit_score.config.Configuration import Configuration
from credit_score.logger import logging
from credit_score.exception import CustomException
from credit_score.entity.config_entity import DataIngestionConfig
from credit_score.entity.config_entity import DataValidationConfig
from credit_score.entity.config_entity import DataTransformationConfig
from credit_score.entity.artifact_entity import DataIngestionArtifact
from credit_score.entity.artifact_entity import DataValidationArtifact
from credit_score.entity.artifact_entity import DataTransformationArtifact
from credit_score.components.data_ingestion import DataIngestion
from credit_score.components.data_validation import DataValidaton
from credit_score.components.data_transformation import DataTransformation
import os, sys
import pandas as pd

class Pipeline():

    def __init__(self,config: Configuration=Configuration())->None:
        try:
            logging.info(f"\n{'*'*20} Initiating the Training Pipeline {'*'*20}\n\n")
            self.config = config
        except Exception as e:
            raise CustomException(e,sys) from e

    def start_data_ingestion(self,data_ingestion_config:DataIngestionConfig)->DataIngestionArtifact:
        try:
            data_ingestion = DataIngestion(data_ingestion_config = data_ingestion_config)
            return data_ingestion.initiate_data_ingestion()
        except Exception as e:
            raise CustomException(e,sys) from e

    
    def start_data_validation(self, data_ingestion_config:DataIngestionConfig,
                                    data_ingestion_artifact:DataIngestionArtifact)->DataValidationArtifact:
        try:
            data_validation = DataValidaton(data_validation_config=self.config.get_data_validation_config(),
                                             data_ingestion_config = data_ingestion_config,
                                             data_ingestion_artifact=data_ingestion_artifact)
            return data_validation.initiate_data_validation()
        except Exception as e:
            raise CustomException(e,sys) from e
        
    def start_data_transformation(self,data_ingestion_artifact: DataIngestionArtifact,
                                       data_validation_artifact: DataValidationArtifact) -> DataTransformationArtifact:
        try:
            data_transformation = DataTransformation(
                data_transformation_config = self.config.get_data_transformation_config(),
                data_ingestion_artifact = data_ingestion_artifact,
                data_validation_artifact = data_validation_artifact)

            return data_transformation.initiate_data_transformation()
        except Exception as e:
            raise CustomException(e,sys) from e

    def run_pipeline(self):
        try:
            data_ingestion_config=self.config.get_data_ingestion_config()

            data_ingestion_artifact = self.start_data_ingestion(data_ingestion_config)

            data_validation_artifact = self.start_data_validation(data_ingestion_config=data_ingestion_config,
                                                            data_ingestion_artifact=data_ingestion_artifact)
            data_transformation_artifact = self.start_data_transformation(data_ingestion_artifact=data_ingestion_artifact,
                                                             data_validation_artifact=data_validation_artifact)
            
        except Exception as e:
            raise CustomException(e, sys) from e
        

    def __del__(self):
        logging.info(f"\n{'*'*20} Training Pipeline Complete {'*'*20}\n\n")