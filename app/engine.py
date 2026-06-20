import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from scipy.cluster.hierarchy import linkage, fcluster, cophenet
from scipy.spatial.distance import pdist

FEATURE_NAMES = [
    "total_keys",
    "max_depth",
    "string_ratio",
    "numeric_ratio",
    "boolean_ratio",
    "array_ratio",
    "object_ratio",
    "null_ratio",
    "avg_string_length",
    "string_length_var",
    "avg_array_size"
]

def extract_raw_stats(data, depth=1):
    """
    Recursively crawl a JSON-like python structure to extract structural statistics.
    """
    stats = {
        "total_keys": 0,
        "max_depth": depth,
        "strings_count": 0,
        "numeric_count": 0,
        "boolean_count": 0,
        "array_count": 0,
        "object_count": 0,
        "null_count": 0,
        "string_lengths": [],
        "array_sizes": []
    }
    
    if isinstance(data, dict):
        stats["total_keys"] += len(data)
        stats["object_count"] += 1
        for k, v in data.items():
            sub_stats = extract_raw_stats(v, depth + 1)
            stats["total_keys"] += sub_stats["total_keys"]
            stats["max_depth"] = max(stats["max_depth"], sub_stats["max_depth"])
            stats["strings_count"] += sub_stats["strings_count"]
            stats["numeric_count"] += sub_stats["numeric_count"]
            stats["boolean_count"] += sub_stats["boolean_count"]
            stats["array_count"] += sub_stats["array_count"]
            stats["object_count"] += sub_stats["object_count"]
            stats["null_count"] += sub_stats["null_count"]
            stats["string_lengths"].extend(sub_stats["string_lengths"])
            stats["array_sizes"].extend(sub_stats["array_sizes"])
            
    elif isinstance(data, list):
        stats["array_count"] += 1
        stats["array_sizes"].append(len(data))
        for item in data:
            sub_stats = extract_raw_stats(item, depth + 1)
            stats["total_keys"] += sub_stats["total_keys"]
            stats["max_depth"] = max(stats["max_depth"], sub_stats["max_depth"])
            stats["strings_count"] += sub_stats["strings_count"]
            stats["numeric_count"] += sub_stats["numeric_count"]
            stats["boolean_count"] += sub_stats["boolean_count"]
            stats["array_count"] += sub_stats["array_count"]
            stats["object_count"] += sub_stats["object_count"]
            stats["null_count"] += sub_stats["null_count"]
            stats["string_lengths"].extend(sub_stats["string_lengths"])
            stats["array_sizes"].extend(sub_stats["array_sizes"])
            
    elif isinstance(data, bool):  # Check bool before int, as bool inherits from int in python
        stats["boolean_count"] += 1
    elif isinstance(data, (int, float)):
        stats["numeric_count"] += 1
    elif isinstance(data, str):
        stats["strings_count"] += 1
        stats["string_lengths"].append(len(data))
    elif data is None:
        stats["null_count"] += 1
        
    return stats

def extract_features(payload):
    """
    Extracts normalized numerical features from an API payload.
    """
    stats = extract_raw_stats(payload)
    
    total_elements = (
        stats["strings_count"] + 
        stats["numeric_count"] + 
        stats["boolean_count"] + 
        stats["array_count"] + 
        stats["object_count"] + 
        stats["null_count"]
    )
    denom = max(1, total_elements)
    
    string_ratio = stats["strings_count"] / denom
    numeric_ratio = stats["numeric_count"] / denom
    boolean_ratio = stats["boolean_count"] / denom
    array_ratio = stats["array_count"] / denom
    object_ratio = stats["object_count"] / denom
    null_ratio = stats["null_count"] / denom
    
    if stats["string_lengths"]:
        avg_str_len = sum(stats["string_lengths"]) / len(stats["string_lengths"])
        str_len_var = sum((x - avg_str_len) ** 2 for x in stats["string_lengths"]) / len(stats["string_lengths"])
    else:
        avg_str_len = 0.0
        str_len_var = 0.0
        
    if stats["array_sizes"]:
        avg_arr_size = sum(stats["array_sizes"]) / len(stats["array_sizes"])
    else:
        avg_arr_size = 0.0
        
    return [
        stats["total_keys"],
        stats["max_depth"],
        string_ratio,
        numeric_ratio,
        boolean_ratio,
        array_ratio,
        object_ratio,
        null_ratio,
        avg_str_len,
        str_len_var,
        avg_arr_size
    ]

class SchemaAuditEngine:
    def __init__(self, linkage_method="ward", distance_metric="euclidean"):
        self.linkage_method = linkage_method
        self.distance_metric = distance_metric
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=2)
        self.anomaly_detector = None
        
        # Keep track of fit data
        self.raw_payloads = []
        self.endpoints = []
        self.labels = []
        self.X_raw = None
        self.X_scaled = None
        self.X_pca = None
        self.cluster_assignments = None
        self.linkage_matrix = None
        self.cophenetic_corr = 0.0
        
    def fit_and_cluster(self, dataset, n_clusters=3):
        """
        Fits the engine on a list of raw payloads and runs Agglomerative Clustering.
        """
        self.raw_payloads = [item["payload"] for item in dataset]
        self.endpoints = [item["endpoint"] for item in dataset]
        self.labels = [item["label"] for item in dataset]
        
        # 1. Feature extraction
        features_list = [extract_features(p) for p in self.raw_payloads]
        self.X_raw = np.array(features_list)
        
        # 2. Standardization
        self.X_scaled = self.scaler.fit_transform(self.X_raw)
        
        # 3. Dimensionality reduction
        self.X_pca = self.pca.fit_transform(self.X_scaled)
        
        # 4. Agglomerative Clustering via scipy (for linkage and flexible metrics)
        # Note: 'ward' linkage requires 'euclidean' distance in scipy
        metric = "euclidean" if self.linkage_method == "ward" else self.distance_metric
        self.linkage_matrix = linkage(self.X_scaled, method=self.linkage_method, metric=metric)
        
        # Assign cluster labels
        self.cluster_assignments = fcluster(self.linkage_matrix, t=n_clusters, criterion="maxclust")
        
        # 5. Model quality metrics
        try:
            c, coph_dists = cophenet(self.linkage_matrix, pdist(self.X_scaled))
            self.cophenetic_corr = c
        except Exception:
            self.cophenetic_corr = 0.0
            
        # 6. Fit Outlier/Drift Detector (Unsupervised Isolation Forest)
        # Contamination is set to a low rate to capture structural anomalies
        self.anomaly_detector = IsolationForest(contamination=0.02, random_state=42)
        self.anomaly_detector.fit(self.X_scaled)
        
    def detect_drift(self, test_payload):
        """
        Evaluates a new payload for structural drift/anomalies.
        Returns a dict containing:
          - is_drift: boolean
          - score: raw anomaly score (lower is more anomalous, typically < 0 is drift)
          - distance_to_closest_centroid: metric of how far it is from clean shapes
          - features: list of raw features
        """
        if self.anomaly_detector is None:
            raise ValueError("Engine is not fitted yet.")
            
        feat = np.array([extract_features(test_payload)])
        feat_scaled = self.scaler.transform(feat)
        
        # Predict: 1 for normal, -1 for drift
        pred = self.anomaly_detector.predict(feat_scaled)[0]
        score = self.anomaly_detector.score_samples(feat_scaled)[0]
        
        # Also compute distance to closest cluster centroid
        # Get centroids of clusters
        centroids = []
        for c_id in np.unique(self.cluster_assignments):
            mask = (self.cluster_assignments == c_id)
            centroids.append(self.X_scaled[mask].mean(axis=0))
            
        dists = [np.linalg.norm(feat_scaled[0] - centroid) for centroid in centroids]
        min_dist = min(dists) if centroids else 0.0
        
        # We classify as drift if the Isolation Forest says -1, OR if centroid distance is extremely large
        # Determine 98th percentile of distances in training set to set an dynamic threshold
        training_dists = []
        for i, row in enumerate(self.X_scaled):
            c_id = self.cluster_assignments[i]
            # find centroid of c_id
            c_mask = (self.cluster_assignments == c_id)
            c_centroid = self.X_scaled[c_mask].mean(axis=0)
            training_dists.append(np.linalg.norm(row - c_centroid))
            
        dist_threshold = np.percentile(training_dists, 98) if training_dists else 5.0
        
        is_drift_by_dist = min_dist > dist_threshold
        is_drift = (pred == -1) or is_drift_by_dist
        
        # Get 2D PCA representation of the new payload
        feat_pca = self.pca.transform(feat_scaled)[0]
        
        return {
            "is_drift": bool(is_drift),
            "score": float(score),
            "anomaly_level": "CRITICAL" if min_dist > dist_threshold * 1.5 else "WARNING" if is_drift else "NORMAL",
            "distance_to_closest_centroid": float(min_dist),
            "distance_threshold": float(dist_threshold),
            "features": feat[0].tolist(),
            "pca_coords": feat_pca.tolist()
        }

    def get_summary_df(self):
        """
        Returns a pandas DataFrame of the fitted data for easy plotting.
        """
        df = pd.DataFrame(self.X_raw, columns=FEATURE_NAMES)
        df["cluster"] = [f"Cluster {c}" for c in self.cluster_assignments]
        df["endpoint"] = self.endpoints
        df["label"] = self.labels
        df["pca_x"] = self.X_pca[:, 0]
        df["pca_y"] = self.X_pca[:, 1]
        
        # Let's calculate local reconstruction score or anomaly score for each training payload
        df["anomaly_score"] = self.anomaly_detector.score_samples(self.X_scaled)
        df["is_anomaly"] = self.anomaly_detector.predict(self.X_scaled) == -1
        return df
