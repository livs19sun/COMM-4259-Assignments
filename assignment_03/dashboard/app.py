from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.utils import resample

# The data file, in the data/ folder next to this app
DATA_FILE = Path(__file__).parent / "data" / "titanic_train_clean.csv"


# Read the data once and keep it in memory between clicks
@st.cache_data
def load_data():
    return pd.read_csv(DATA_FILE)


# Split the data into features X and the target y (Survived, 1 = survived).
# PassengerId is only an ID, so it is dropped.
titanic = load_data()
X = titanic.drop(["PassengerId", "Survived"], axis=1)
y = titanic["Survived"]


# The same decision tree every time, so only the evaluation method changes
def make_tree(depth):
    return DecisionTreeClassifier(max_depth=depth, criterion="entropy", random_state=42)


# Holdout: one stratified train/test split (the same split is used for the
# accuracy, the confusion matrix and the cost)
def holdout_split(test_size):
    return train_test_split(X, y, test_size=test_size, stratify=y, random_state=1)


# k-fold cross validation: one accuracy per fold
def cv_scores(depth, k):
    folds = StratifiedKFold(n_splits=k, shuffle=True, random_state=1)
    return cross_val_score(make_tree(depth), X, y, cv=folds)


# Bootstrap: in round b, draw len(X) rows with replacement (random_state=b),
# train on them and test on the rows that were not drawn (out-of-bag).
# Also keeps how many out-of-bag rows each round was tested on.
# Cached because 200 rounds take a few seconds.
@st.cache_data
def bootstrap_scores(depth, rounds):
    rows = np.arange(len(X))
    scores = []
    oob_sizes = []
    for b in range(rounds):
        train_rows = resample(rows, replace=True, n_samples=len(X), random_state=b)
        test_rows = np.setdiff1d(rows, train_rows)
        tree = make_tree(depth).fit(X.iloc[train_rows], y.iloc[train_rows])
        scores.append(accuracy_score(y.iloc[test_rows], tree.predict(X.iloc[test_rows])))
        oob_sizes.append(len(test_rows))
    return np.array(scores), np.array(oob_sizes)


# Page title and the one tab
st.set_page_config(page_title="Model Evaluation", layout="wide")
st.title("Assignment 3: Model Evaluation")
(tab,) = st.tabs(["Model Evaluation"])

with tab:
    # Model settings: these apply to every section below
    st.header("Model settings")
    depth = st.slider("max_depth of the decision tree", min_value=1, max_value=15, value=3)
    test_size = st.slider("Holdout test size (share of passengers held out)",
                          min_value=0.10, max_value=0.50, value=0.30, step=0.05)
    st.code(f'DecisionTreeClassifier(max_depth={depth}, criterion="entropy", random_state=42)')
    st.caption(f"Data: {len(X)} passengers, {X.shape[1]} features. Positive class: Survived = 1.")

    # Train the tree on the holdout split once; sections 1, 2 and 3 all use it
    X_train, X_test, y_train, y_test = holdout_split(test_size)
    tree = make_tree(depth).fit(X_train, y_train)
    y_pred = tree.predict(X_test)

    # ---------- 1. Validation method and accuracy ----------
    st.header("1. Accuracy by validation method")
    method = st.radio("Validation method",
                      ["Holdout", "k-fold cross validation", "Bootstrap"], horizontal=True)

    # Holdout: accuracy on the passengers that were held out
    if method == "Holdout":
        acc = accuracy_score(y_test, y_pred)
        col1, col2, col3 = st.columns(3)
        col1.metric(f"Holdout accuracy ({len(y_test)} test passengers)", f"{acc:.2%}")
        col2.metric("Training rows", len(X_train))
        col3.metric("Test rows", len(X_test))
        st.code(f"X_train, X_test, y_train, y_test = train_test_split(X, y, test_size={test_size:.2f}, stratify=y, random_state=1)\n"
                "accuracy_score(y_test, tree.predict(X_test))\n"
                "len(X_train), len(X_test)   # rows used to train and to test")

    # Cross validation: mean and standard deviation of the k fold accuracies
    elif method == "k-fold cross validation":
        k = st.slider("Number of folds k", min_value=3, max_value=10, value=5)
        scores = cv_scores(depth, k)
        # Standard error of the mean: how much the mean itself could move
        std_error = scores.std() / np.sqrt(k)
        col1, col2, col3 = st.columns(3)
        col1.metric("Mean accuracy", f"{scores.mean():.2%}")
        col2.metric("Standard deviation", f"{scores.std():.2%}")
        col3.metric("Standard error (SD / √k)", f"{std_error:.2%}")

        # Rows in each fold: the same folds cross_val_score used
        folds = StratifiedKFold(n_splits=k, shuffle=True, random_state=1)
        fold_rows = [(len(train), len(test)) for train, test in folds.split(X, y)]
        st.dataframe(pd.DataFrame({"Fold": range(1, k + 1),
                                   "Training rows": [r[0] for r in fold_rows],
                                   "Test rows": [r[1] for r in fold_rows],
                                   "Accuracy": [f"{s:.2%}" for s in scores]}),
                     hide_index=True)
        st.code(f"folds = StratifiedKFold(n_splits={k}, shuffle=True, random_state=1)\n"
                "scores = cross_val_score(make_tree(depth), X, y, cv=folds)\n"
                "scores.mean(), scores.std()\n"
                f"scores.std() / np.sqrt({k})   # standard error\n"
                "[(len(train), len(test)) for train, test in folds.split(X, y)]   # rows per fold")

    # Bootstrap: mean out-of-bag accuracy and the middle 95% of the rounds
    else:
        rounds = st.slider("Number of bootstrap rounds", min_value=10, max_value=200, value=100)
        scores, oob_sizes = bootstrap_scores(depth, rounds)
        low, high = np.percentile(scores, 2.5), np.percentile(scores, 97.5)
        col1, col2 = st.columns(2)
        col1.metric("Mean out-of-bag accuracy", f"{scores.mean():.2%}")
        col2.metric("Middle 95% of rounds", f"{low:.2%} to {high:.2%}")
        col3, col4 = st.columns(2)
        col3.metric("Rounds used", len(scores))
        col4.metric("Out-of-bag test rows per round",
                    f"{oob_sizes.mean():.0f} on average ({oob_sizes.min()} to {oob_sizes.max()})")
        st.caption(f"Each round trains on {len(X)} rows drawn with replacement.")
        st.code(f"for b in range({rounds}):\n"
                "    train_rows = resample(rows, replace=True, n_samples=len(X), random_state=b)\n"
                "    test_rows = np.setdiff1d(rows, train_rows)   # out-of-bag passengers\n"
                "    accuracy_score(y.iloc[test_rows], tree.predict(X.iloc[test_rows]))\n"
                "np.percentile(scores, 2.5), np.percentile(scores, 97.5)\n"
                "len(scores)   # rounds used\n"
                "len(test_rows)   # out-of-bag rows in one round")

    # ---------- 2. Confusion matrix on the holdout split ----------
    st.header("2. Confusion matrix (holdout split)")
    st.caption(f"Test size {test_size:.2f}: {len(y_test)} passengers. Rows are actual, columns are predicted.")

    # labels=[1, 0] puts Survived = 1 in the first row and first column
    cm = confusion_matrix(y_test, y_pred, labels=[1, 0])
    st.dataframe(pd.DataFrame(cm,
                              index=["Actual: Survived (1)", "Actual: Did not survive (0)"],
                              columns=["Predicted: Survived (1)", "Predicted: Did not survive (0)"]))
    st.code("confusion_matrix(y_test, y_pred, labels=[1, 0])")

    # Precision, recall and F1 for the positive class (Survived = 1).
    # zero_division=0 shows 0.00% instead of an error if no one is predicted to survive.
    precision = precision_score(y_test, y_pred, pos_label=1, zero_division=0)
    recall = recall_score(y_test, y_pred, pos_label=1, zero_division=0)
    f1 = f1_score(y_test, y_pred, pos_label=1, zero_division=0)
    col1, col2, col3 = st.columns(3)
    col1.metric("Precision (Survived)", f"{precision:.2%}")
    col2.metric("Recall (Survived)", f"{recall:.2%}")
    col3.metric("F1 (Survived)", f"{f1:.2%}")
    st.code("precision_score(y_test, y_pred, pos_label=1)\n"
            "recall_score(y_test, y_pred, pos_label=1)\n"
            "f1_score(y_test, y_pred, pos_label=1)")

    # ---------- 3. Cost of the holdout predictions ----------
    st.header("3. Total cost of the holdout predictions")

    # Read the false positives and false negatives from the confusion matrix
    TP, FN = cm[0, 0], cm[0, 1]   # actual Survived: predicted Survived, predicted Did not survive
    FP, TN = cm[1, 0], cm[1, 1]   # actual Did not survive: predicted Survived, predicted Did not survive

    # The user types in the cost of each kind of mistake
    col1, col2 = st.columns(2)
    cost_fp = col1.number_input("Cost of a false positive (predicted Survived, actually did not)",
                                min_value=0.0, value=1.0, step=1.0)
    cost_fn = col2.number_input("Cost of a false negative (predicted Did not survive, actually survived)",
                                min_value=0.0, value=1.0, step=1.0)

    # Total cost = number of each mistake x its cost
    total_cost = FP * cost_fp + FN * cost_fn
    st.metric("Total cost", f"{total_cost:,.2f}")
    st.write(f"{FP} false positives x {cost_fp:,.2f} + {FN} false negatives x {cost_fn:,.2f} = {total_cost:,.2f}")
    st.code("TP, FN, FP, TN = cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]\n"
            "total_cost = FP * cost_fp + FN * cost_fn")
