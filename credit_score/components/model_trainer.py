from credit_score.logger import logging
from credit_score.exception import CustomException
from credit_score.entity.config_entity import *
from credit_score.entity.artifact_entity import *
from credit_score.constant import *
from credit_score.utils.utils import save_object
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import f1_score
from xgboost import XGBClassifier
import pandas as pd
import numpy as np
import os, sys
import optuna 


class ModelTrainer:

    def __init__(self,
                 model_trainer_config: ModelTrainerConfig,
                 data_transformation_artifact: DataTransformationArtifact):
        try:
            logging.info(f"\n{'*'*20} Model Training started {'*'*20}\n\n")
            self.model_trainer_config = model_trainer_config
            self.data_transformation_artifact = data_transformation_artifact
        except Exception as e:
            raise CustomException(e, sys) from e
        
    def get_random_forest_best_params(self,x_train,y_train)-> dict:
        try:
            logging.info("Grid Search for Random forest best parameters started")
            rf = RandomForestClassifier(
                n_estimators= 100,
                criterion= 'gini',
                random_state= 786
            ) 
            params ={
                "n_estimators" : [50,100,150,200],
                "max_depth" : [2,3,4,5,6,7,8,9],
                "min_samples_split" : [2,4,5,6,10],
                "criterion" : ["gini", "entropy", "log_loss"],
                "max_features": ["sqrt", "log2", None],

            }
            grid_rf = GridSearchCV(
                estimator= rf,
                param_grid= params,
                cv= 10,
                scoring="f1_score"
            )
            grid_rf.fit(x_train,y_train)
            logging.info("Grid Search for Random forest best parameters completed")
            return grid_rf.best_params_
        except Exception as e:
            raise   CustomException(e, sys) from e
    
    def get_xgboost_best_params(self,x_train,x_test,y_train,y_test)-> dict:
        try:
            logging.info("Optuna Search for XG Boost best parameters started")
            def objective(trial, data=x_train, target=y_train):
                param = {
                #'tree_method' : 'gpu_hist',
                'lambda' : trial.suggest_loguniform('lambda', 1e-4, 10.0),
                'alpha' :  trial.suggest_loguniform('alpha', 1e-4, 10.0),
                'colsample_bytree' : trial.suggest_categorical('colsample_bytree', [.1,.2,.3,.4,.5,.6,.7,.8,.9,1]),
                'subsample' : trial.suggest_categorical('subsample', [.1,.2,.3,.4,.5,.6,.7,.8,.9,1]),
                'learning_rate' : trial.suggest_categorical('learning_rate',[.00001,.0003,.008,.02,.01,0.10,0.15,0.2,1,10,20]),
                'n_estimator' : 130,
                'max_depth' : trial.suggest_categorical('max_depth', [3,4,5,6,7,8,9,10,11,12]),
                'random_state' : 786,
                'min_child_weight' : trial.suggest_int('min_child_weight',1,200),
                'booster' : trial.suggest_categorical('booster',["gblinear","gbtree","dart"]),
                "reg_lambda" : trial.suggest_categorical("reg_lambda",[0.01, 0.05, 0.10]),
                "reg_alpha" : trial.suggest_categorical("reg_alpha",[0.01, 0.05, 0.10]),
                'verbosity' : 2
                }
                if param["booster"] in ['gbtree', 'dart']:
                    param['gamma'] : trial.suggest_float('gamma', 1e-3, 4)
                    param['eta'] : trial.suggest_float('eta', .001, 5)

                xgb_class_model = XGBClassifier(
                    objective="class:f1_score",
                    **param
                )
                xgb_class_model.fit(data,target, eval_set = [(x_test,y_test)], verbose = True)
                pred_xgb = xgb_class_model.predict(x_test)
                f1_Score = f1_score(x_test, pred_xgb)
                return f1_Score
            
            find_param = optuna.create_study(direction='minimize')
            find_param.optimize(objective, n_trials = 10)
            find_param.best_trial.params
            logging.info("Optuna Search for XG Boost best parameters completed")
            params = find_param.best_trial.params
            return params
        except ValueError:
            return self.get_xgboost_best_params(x_train,y_train,x_test,y_test)
        except Exception as e:
            raise CustomException(e, sys) from e
        
    def Random_Forest_Classifier(self,x_train,y_train):
        try:
            logging.info("Getting Best Parameters for Random Forest by Grid Search CV")
            rf_best_params = self.get_random_forest_best_params(x_train,y_train)

            logging.info(f"RF Best Parameters : {rf_best_params}")
            logging.info("Fitting random forest model")
            rf = RandomForestClassifier(
                **rf_best_params,
                criterion="f1_score",
                random_state=786
            )
            rf.fit(x_train,y_train)

            return rf
        except Exception as e:
            raise CustomException(e,sys) from e
        
    def XGBoost_Classifier(self,x_train,y_train,x_test,y_test):
        try:
            logging.info("Getting Best Parameters for Random Forest by Grid Search CV")
            xgb_best_params = self.get_xgboost_best_params(x_train,y_train,x_test,y_test)

            logging.info(f"XGB Best Parameters : {xgb_best_params}")
            logging.info("Fitting XG Boost model")
            xgb = XGBClassifier(
                objective="class:f1_score",
                n_estimator=130, 
                random_state = 786,
                **xgb_best_params
            )
            xgb.fit(x_train,y_train)

            return xgb
        except Exception as e:
            raise CustomException(e,sys) from e
        
    def get_best_model(self,x_train,y_train,x_test,y_test):
        try:
            logging.info(f"{'*'*20} Training XGBoost Model {'*'*20}")
            xgb_obj = self.XGBoost_Classifier(x_train,y_train,x_test,y_test)
            logging.info(f"{'*'*20} Trained XGBoost Model Successfully!! {'*'*20}")

            logging.info(f"{'*'*20} Training Random Forest Model {'*'*20}")
            rf_obj = self.Random_Forest_Classifier(x_train,y_train)
            logging.info(f"{'*'*20} Trained Random Forest Model Successfully!! {'*'*20}")

            logging.info("***Objects for model obtained!!! Now calcalating R2 score for model evaluation***")
            rf_f1_train = f1_score(y_train,rf_obj.predict(x_train))
            xgb_f1_train = f1_score(y_train,xgb_obj.predict(x_train))
            logging.info(f"f1 score for Training set ---> Random Forest: {rf_f1_train} || XG Boost: {xgb_f1_train}")
            
            rf_f1_test = f1_score(y_test, rf_obj.predict(x_test))
            xgb_f1_test = f1_score(y_test, xgb_obj.predict(x_test))
            logging.info(f"f1 score for Testing set ---> Random Forest : {rf_f1_test} || XGBoost : {xgb_f1_test}")

            if xgb_f1_test > rf_f1_test:
                logging.info("XGBoost Model Accepted!!!")
                return xgb_obj
            else:
                logging.info("Random Forest Model Accepted!!!")
                return rf_obj

        except Exception as e:
            raise CustomException(e,sys) from e


    def initiate_model_training(self) -> ModelTrainerArtifact:
        try:
            logging.info("Finding transformed Training and Test")
            transformed_train_file_path = self.data_transformation_artifact.transformed_train_file_path
            transformed_test_file_path = self.data_transformation_artifact.transformed_test_file_path

            logging.info("Transformed Data found!!! Now, converting it into dataframe")
            train_df = pd.read_csv(transformed_train_file_path)
            test_df = pd.read_csv(transformed_test_file_path)

            train_df = train_df.infer_objects()
            test_df = test_df.infer_objects()

            logging.info("Splitting Input features and Target Feature for train and test data")
            train_input_feature = train_df.drop(columns=['Credit_Score'], axis= 1)
            train_target_feature = train_df.iloc[:,-1]

            test_input_feature = test_df.drop(columns=["Credit_score"], axis=1)
            test_target_feature = test_df.iloc[:,-1]

            logging.info("Best Model Finder function called")
            model_obj = self.get_best_model(train_input_feature,train_target_feature,test_input_feature,test_target_feature)

            logging.info("Saving best model object file")
            trained_model_object_file_path = self.model_trainer_config.trained_model_file_path
            save_object(file_path=trained_model_object_file_path, obj=model_obj)
            save_object(file_path=os.path.join(ROOT_DIR,PIKLE_FOLDER_NAME_KEY,
                                 os.path.basename(trained_model_object_file_path)),obj=model_obj)


            model_trainer_artifact = ModelTrainerArtifact(is_trained=True, 
                                                          message="Model Training Done!!",
                                                          trained_model_object_file_path=trained_model_object_file_path)
            
            logging.info(f"Model Trainer Artifact: {model_trainer_artifact}")
            return model_trainer_artifact
        except Exception as e:
            raise CustomException(e,sys) from e
        
    def __del__(self):
        logging.info(f"\n{'*'*20} Model Training log completed {'*'*20}\n\n")
        