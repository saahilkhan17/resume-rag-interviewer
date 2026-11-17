---
roles: [ai-ml-engineer, data-science]
topics: [decision trees, random forests, gradient boosting]
---
# Decision Trees and Ensembles

A decision tree splits data recursively by choosing the feature and threshold that best separates the target, measured by impurity criteria such as Gini impurity or entropy (information gain). Leaves predict the majority class or the mean value. Trees are interpretable and handle mixed feature types, but a single deep tree overfits easily.

Random forests train many trees on bootstrap samples of the data and random subsets of features at each split, then average (regression) or vote (classification). Bagging reduces variance without increasing bias much, which is why forests generalise better than single trees.

Gradient boosting builds trees sequentially: each new tree fits the residual errors of the ensemble so far. Implementations such as XGBoost, LightGBM and CatBoost add regularization, efficient split finding and handling of missing values. Boosting often wins tabular competitions but needs careful tuning of learning rate, tree depth and number of trees to avoid overfitting.

Feature importance from tree ensembles is useful for exploration but is biased toward high-cardinality features and correlated groups; permutation importance is a more honest check.
