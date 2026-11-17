---
roles: [ai-ml-engineer, data-science]
topics: [evaluation metrics, precision, recall, ROC-AUC, cross-validation]
---
# Evaluation Metrics and Cross-Validation

Accuracy is the fraction of correct predictions, but it misleads on imbalanced data: a model that always predicts the majority class can score 95 percent accuracy while being useless. Precision is the fraction of predicted positives that are truly positive; recall is the fraction of true positives the model finds. The F1 score is their harmonic mean. Which matters depends on the cost of errors: missing a fraud case (low recall) versus flagging innocent users (low precision).

The confusion matrix (true/false positives and negatives) makes these tradeoffs visible. ROC-AUC measures ranking quality across all thresholds; precision-recall AUC is more informative for heavily imbalanced problems. For regression, common metrics are mean absolute error, mean squared error and R-squared.

Cross-validation estimates generalisation honestly: k-fold splits the data into k parts, trains on k-1 and validates on the held-out part, rotating so every point is validated once. Stratified folds preserve class ratios. Time-series data needs time-based splits, never random shuffling, or future information leaks into training.
