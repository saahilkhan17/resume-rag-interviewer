---
roles: [ai-ml-engineer, data-science]
topics: [unsupervised learning, clustering, dimensionality reduction]
---
# Unsupervised Learning, Clustering and Dimensionality Reduction

Unsupervised learning finds structure in data without labels. Clustering groups similar points: k-means assigns points to the nearest of k centroids and iterates; choosing k uses the elbow method or silhouette score. DBSCAN finds dense regions and labels sparse points as noise, which handles oddly shaped clusters and outliers better than k-means.

Hierarchical clustering builds a tree of merges or splits and is useful when the number of clusters is unknown, but it scales poorly to large datasets. Gaussian mixture models give soft assignments and model cluster shapes with covariance.

Dimensionality reduction compresses features while preserving structure. PCA finds orthogonal directions of maximum variance and is exact and fast; t-SNE and UMAP preserve local neighbourhoods for visualisation but distort global distances and should not be used for downstream distance measurements.

Evaluation is harder without labels: use intrinsic measures (silhouette, Davies-Bouldin), stability across subsamples, and whether the clusters are actionable for the actual business question. Clustering on unscaled features lets the largest-magnitude feature dominate, so standardisation comes first.
