import xgboost as xgb
from sklearn.base import BaseEstimator, RegressorMixin


class XGBMetaLearner(BaseEstimator, RegressorMixin):
    def __init__(self, params=None):
        self.params = params or {
            "n_estimators": 100,
            "max_depth": 3,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "objective": "reg:squarederror",  # Ou 'binary:logistic' selon votre cas
        }
        self.model = xgb.XGBRegressor(**self.params)

    def fit(self, meta_features, y):
        """
        meta_features: Array de forme (n_samples, n_base_models)
        contenant les prédictions OOF des modèles de Phase 1.
        """
        self.model.fit(meta_features, y)
        return self

    def predict(self, meta_features):
        return self.model.predict(meta_features)

    def save_model(self, path="meta_model.ubj"):
        self.model.save_model(path)
