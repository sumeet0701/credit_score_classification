from credit_score.utils.utils import read_yaml_file
from credit_score.utils.utils import save_data
from credit_score.utils.utils import save_object
from credit_score.utils.utils import load_data
from credit_score.utils.utils import save_numpy_array_data
from credit_score.logger import logging
from credit_score.exception import CustomException
from credit_score.constant import *
from credit_score.entity.artifact_entity import DataIngestionArtifact
from credit_score.entity.artifact_entity import DataValidationArtifact
from credit_score.entity.artifact_entity import DataTransformationArtifact
from credit_score.entity.config_entity import DataTransformationConfig
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import PowerTransformer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer 
from imblearn.combine import SMOTEENN
import os,sys
import pandas as pd
import numpy as np
import re


class DataTransformation:

    def __init__(self,
                 data_transformation_config: DataTransformationConfig,
                 data_ingestion_artifact: DataIngestionArtifact,
                 data_validation_artifact: DataValidationArtifact):
        try:
            logging.info(f"{'>>' * 30}Data Transformation log started.{'<<' * 30}")
            self.data_transformation_config = data_transformation_config
            self.data_ingestion_artifact = data_ingestion_artifact
            self.data_validation_artifact = data_validation_artifact
        except Exception as e:
            raise CustomException(e, sys) from e
        
    def get_data_transformer_object(self)->ColumnTransformer:
        try:
            schema_file_path = self.data_validation_artifact.schema_file_path
            dataset_schema = read_yaml_file(file_path= schema_file_path)

            numerical_columns = dataset_schema[NUMERICAL_COLUMN_KEY]
            ordinal_columns = dataset_schema[ORDINAL_COLUMN_KEY]
            onehot_columns = dataset_schema[ONE_HOT_COLUMN_KEY]
            transform_columns = dataset_schema[TRANSFORM_COLUMN_KEY]

            num_pipeline = Pipeline(steps=[
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', MinMaxScaler())
            ])

            onehot_pipeline= Pipeline(steps=[
                ('imputer', SimpleImputer(strategy='most_frequent')),
                ('label_encoder', LabelEncoder()),
                ('scaler', StandardScaler(with_mean=False))
            ])
            ordinal_pipeline = Pipeline(steps=[
                ('imputer', SimpleImputer(strategy='most_frequent')),
                ('one_hot_encoder', OrdinalEncoder()),
                ('scaler', StandardScaler(with_mean=False))
            ])

            # Power transforms are a family of parametric, monotonic transformations that are applied to make data more Gaussian-like.
            transform_pipeline = Pipeline(steps=[
                ('scaler', MinMaxScaler()),
                ('transformer', PowerTransformer())
            ])

 # ColumnTransformer enables us to apply transform to particular columns. 
# It help us to fit multiple transformations to multiple columns with a single fit() or fit_transform() statement.

            preprocessor = ColumnTransformer([
                ('num_pipeline', num_pipeline, numerical_columns),
                ('onehot_pipeline', onehot_pipeline, onehot_columns),
                ('ordinal_pipeline', ordinal_pipeline, ordinal_columns),
                ('power_transformer', transform_pipeline, transform_columns)
            ])
                         
            return preprocessor
        
        except Exception as e:
            raise CustomException(e, sys) from e
        
    def _remove_outliers_IQR(self, col, df):
        try:
            percentile25 = df[col].quantile(0.25)
            percentile75 = df[col].quantile(0.75)
            iqr = percentile75 - percentile25
            upper_limit = percentile75 + 1.5 * iqr
            lower_limit = percentile25 - 1.5 * iqr
            df.loc[(df[col]>upper_limit), col]= upper_limit
            df.loc[(df[col]<lower_limit), col]= lower_limit 
            return df
        
        except Exception as e:
            raise CustomException(e, sys) from e 
        
    
    def initiate_data_transformation(self) -> DataTransformationArtifact:
        try:
            logging.info(f"Obtaining preprocessing object.")
            preprocessing_obj = self.get_data_transformer_object()

            logging.info(f"Obtaining training and test file path.")
            train_file_path = self.data_ingestion_artifact.train_file_path
            test_file_path = self.data_ingestion_artifact.test_file_path

            schema_file_path = self.data_validation_artifact.schema_file_path

            logging.info(f"Loading training and test data as pandas dataframe.")
            train_df = load_data(file_path=train_file_path, schema_file_path=schema_file_path)

            test_df = load_data(file_path=test_file_path, schema_file_path=schema_file_path)

            schema = read_yaml_file(file_path=schema_file_path)

            target_column_name = schema[TARGET_COLUMN_KEY]
            numerical_columns = schema[NUMERICAL_COLUMN_KEY]

            logging.info(f"{numerical_columns}")

            continuous_columns = ['Age','Annual_Income','Monthly_Inhand_Salary','Interest_Rate',
                                  'Delay_from_due_date','Num_of_Delayed_Payment','Changed_Credit_Limit',
                                  'Outstanding_Debt','Credit_Utilization_Ratio', 'Credit_History_Age',
                                  'Total_EMI_per_month','Amount_invested_monthly','Monthly_Balance']
            #continuous_columns=[feature for feature in numerical_columns if len(train_df[feature].unique())>=25]
            #continuous_columns=[feature for feature in numerical_columns if len(train_df[feature].unique())>=25]
            #logging.info(f"{continuous_columns}")
            
            for col in continuous_columns:
                self._remove_outliers_IQR(col=col, df= train_df)
            
            logging.info(f"Outlier capped in train df")
            
            for col in continuous_columns:
                self._remove_outliers_IQR(col=col, df= test_df)
                
            logging.info(f"Outlier capped in test df")            

            logging.info(f"Splitting input and target feature from training and testing dataframe.")
            input_feature_train_df = train_df.drop(columns=[target_column_name], axis=1)
            target_feature_train_df = train_df[target_column_name]
            print(input_feature_train_df)

            input_feature_test_df = test_df.drop(columns=[target_column_name], axis=1)
            target_feature_test_df = test_df[target_column_name]
            logging.info(f"{input_feature_train_df.columns}")
            logging.info(f"{target_feature_train_df}")
            logging.info(f"{input_feature_test_df.columns}")
            logging.info(f"{target_feature_test_df}")
            logging.info(f"{preprocessing_obj.fit_transform(input_feature_train_df)}")

            logging.info(f"Applying preprocessing object on training dataframe and testing dataframe.")
            input_feature_train_arr = preprocessing_obj.fit_transform(input_feature_train_df)
            input_feature_test_arr = preprocessing_obj.transform(input_feature_test_df)
            
            smt = SMOTEENN(random_state=42,sampling_strategy='all') # all
            
            input_feature_train_arr, target_feature_train_df = smt.fit_resample(input_feature_train_arr, target_feature_train_df)
            
            input_feature_test_arr, target_feature_test_df = smt.fit_resample(input_feature_test_arr , target_feature_test_df)

            train_arr = np.c_[input_feature_train_arr, np.array(target_feature_train_df)]

            test_arr = np.c_[input_feature_test_arr, np.array(target_feature_test_df)]

            transformed_train_dir = self.data_transformation_config.transformed_train_dir
            transformed_test_dir = self.data_transformation_config.transformed_test_dir

            train_file_name = os.path.basename(train_file_path).replace(".csv", ".npz")
            test_file_name = os.path.basename(test_file_path).replace(".csv", ".npz")

            transformed_train_file_path = os.path.join(transformed_train_dir, train_file_name)
            transformed_test_file_path = os.path.join(transformed_test_dir, test_file_name)

            logging.info(f"Saving transformed training and test array.")

            save_numpy_array_data(file_path=transformed_train_file_path, array=train_arr)
            save_numpy_array_data(file_path=transformed_test_file_path, array=test_arr)

            preprocessing_obj_file_path = self.data_transformation_config.preprocessed_object_file_path

            logging.info(f"Saving preprocessing object.")
            save_object(file_path=preprocessing_obj_file_path, obj=preprocessing_obj)

            data_transformation_artifact = DataTransformationArtifact(is_transformed=True,
                                                                      message="Data transformation successfull.",
                                                                      transformed_train_file_path=transformed_train_file_path,
                                                                      transformed_test_file_path=transformed_test_file_path,
                                                                      preprocessed_object_file_path=preprocessing_obj_file_path
                                                                      )
            logging.info(f"Data transformation artifact: {data_transformation_artifact}")
            return data_transformation_artifact
        except Exception as e:
            raise CustomException(e, sys) from e

    def __del__(self):
        logging.info(f"{'>>' * 30}Data Transformation log completed.{'<<' * 30} \n\n")
        

