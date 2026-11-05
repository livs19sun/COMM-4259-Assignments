# Assignment 3: Model Evaluation app

A one-tab Streamlit app, **Model Evaluation**, that shows how the way a decision tree is evaluated changes what you conclude about it. It uses the prepared Titanic data in `data/titanic_train_clean.csv`. The target is `Survived`, the positive class is 1, and `PassengerId` is dropped. The app makes no decisions on its own and uses no AI model.

## What the tab shows

- **Model settings**: a `max_depth` slider (1 to 15) for `DecisionTreeClassifier(criterion="entropy", random_state=42)`, and a holdout test-size slider (0.10 to 0.50, default 0.30). Everything below uses these settings.
- **1. Accuracy by validation method**: choose one method.
  - **Holdout**: one stratified `train_test_split` (`random_state=1`), with accuracy on the held-out passengers.
  - **k-fold cross validation**: `StratifiedKFold` (k from 3 to 10, `shuffle=True`, `random_state=1`), showing the mean and standard deviation of the fold accuracies plus each fold's score.
  - **Bootstrap**: 10 to 200 rounds. Round b draws a sample with `resample(..., random_state=b)` and tests on the out-of-bag passengers. Shows the mean accuracy and the middle 95% of the rounds.
- **2. Confusion matrix** on the same holdout split (rows actual, columns predicted, Survived = 1 first), with precision, recall and F1 for Survived = 1.
- **3. Total cost**: type in the cost of a false positive and of a false negative. The app shows the total cost of the holdout predictions.

Every rate is shown as a percentage with two decimals, and each result shows the scikit-learn line it comes from.

## How to run it

From the `comm4259` (repository) folder:

```
pip install -r assignment_03/dashboard/requirements.txt
streamlit run assignment_03/dashboard/app.py
```

The app opens in your browser at http://localhost:8501.

## Why holdout and cross validation accuracies can differ

A **holdout** accuracy comes from a single split: the tree is trained on one part of the data and tested once on the rest (268 passengers for a 30% split). The number depends on which passengers happened to land in that test set. A different split, or a different test size, could give a noticeably higher or lower accuracy.

**Cross validation** splits the data into k folds and tests k times, so every passenger is in a test set exactly once. It reports the average of the k accuracies. Because it averages over several test sets and uses all 891 passengers for testing, it is usually a more stable estimate. Its standard deviation shows how much the accuracy moves from one fold to the next, which is roughly how much a single holdout number could be off by.

So the two methods answer the same question ("how well does this tree predict new passengers?") using different test passengers, and their answers differ by chance. Neither one is wrong. Cross validation simply relies less on one lucky or unlucky split.
