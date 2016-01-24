# coding=utf-8
import pandas as pd
from sklearn.cross_validation import train_test_split
from sklearn.grid_search import GridSearchCV
from sklearn.metrics import classification_report
from sklearn.ensemble import RandomForestClassifier
from sklearn.externals import joblib
import cPickle
import re

class MyClassifierEngine:
    def __init__(self):
        pass
    def loadFirstDF(self):
        return pd.read_csv("../input/all_summary.txt", sep=";", na_values=["nan"])
    def loadResNames(self):
        return pd.read_csv("../input/grouped_res_name.txt", sep=",", na_values=["nan"])
    def loadTestDataDF(self):
        return pd.read_csv("../input/test_data.txt", sep=",", na_values=["nan"])
    def filterColumns(self, df):
        columnsWithStringValues = ["title", "chain_id", "res_id"]
        columnsWithOnlyNas = ["local_BAa", "local_NPa", "local_Ra", "local_RGa", "local_SRGa", "local_CCSa", "local_CCPa", "local_ZOa", "local_ZDa", "local_ZD_minus_a", "local_ZD_plus_a", "weight_col"]
        columnsWithSameValue = ["local_min", "fo_col", "fc_col", "grid_space", "solvent_radius", "solvent_opening_radius", "resolution_max_limit", "part_step_FoFc_std_min", "part_step_FoFc_std_max", "part_step_FoFc_std_step"]
        columnsToRemovePattern1 = r'^part_0[1-9].*'
        columnsToRemovePattern2 = r'^part_1.*'
        correctColumns = []
        for e in df.columns:
            if not( e in columnsWithStringValues or e in columnsWithOnlyNas or e in columnsWithSameValue or re.search(columnsToRemovePattern1, e) or re.search(columnsToRemovePattern2, e)):
                correctColumns.append(e)
        return df.loc[:, correctColumns]
    def filterColumnsForTestData(self, df):
        df = self.filterColumns(df)
        columnsLackingInTestData = ["local_res_atom_count", "local_res_atom_non_h_count", "local_res_atom_non_h_occupancy_sum", "local_res_atom_non_h_electron_sum", "local_res_atom_non_h_electron_occupancy_sum", "local_res_atom_C_count", "local_res_atom_N_count", "local_res_atom_O_count", "local_res_atom_S_count", "dict_atom_non_h_count", "dict_atom_non_h_electron_sum", "dict_atom_C_count", "dict_atom_N_count", "dict_atom_O_count", "dict_atom_S_count", "local_volume", "local_electrons", "local_mean", "local_std"]
        correctColumns = []
        for e in df.columns:
            if not(e in columnsLackingInTestData):
                correctColumns.append(e)
        return df.loc[:, correctColumns]
    def filterRowsByResName(self, df):
        forbiddenResName = ["DA","DC","DT", "DU", "DG", "DI","UNK", "UNX", "UNL", "PR", "PD", "Y1", "EU", "N", "15P", "UQ", "PX4", "NAN"]
        return df[df["res_name"].apply(lambda x: not (x in forbiddenResName))]
    def filterRwosByDistinctPairs(self, df):
        e = []
        distinctSet = set([])
        for i in df.index:
            value = "{}_{}".format(df.loc[i,"pdb_code"],df.loc[i,"res_name"])
            if(value in distinctSet):
                e.append(False)
            else :
                distinctSet.add(value)
                e.append(True)
        return df[e]
    def filterRowsByGroupSize(self, df, column="res_name", value = 5):
        f = df.groupby(column).size()
        return df[df[column].apply(lambda x: (pd.isnull(x) or (f[x] >= value)))]
    def learnClfRandomForest(self, X, y, printBestParams = True, printClassificationReport = True):
        X_train, X_test, y_train, y_test = train_test_split(X, y, train_size=0.75, random_state=0)
        tuned_parameters = [{"max_depth": [10,50,None],
                     "criterion": ["gini","entropy"],
                     "n_estimators": [2,10,30]}]
        scores = ['recall']

        for score in scores:
            clf = GridSearchCV(RandomForestClassifier(), tuned_parameters, cv=5, scoring='%s_weighted' % score)
            clf.fit(X_train, y_train)
            if(printBestParams):
                print(clf.best_params_)

        y_true, y_pred = y_test, clf.predict(X_test)
        if(printClassificationReport):
            print(classification_report(y_true, y_pred))
        return clf
    def saveTestClassification(self, fileName, data):
        f = open('../{}.txt'.format(fileName),'w')
        j=1
        f.write('"","res_name"\n')
        for i in data:
            f.write('"{}","{}"\n'.format(j,i))
            j += 1
        f.close()
    def exportClf(self, clf, fileName):
        joblib.dump(clf.best_estimator_, '{}.pkl'.format(fileName))
        with open('{}.pickle'.format(fileName), 'wb') as f:
            cPickle.dump(clf.best_estimator_, f)
    def importClf(self, fileName):
        with open('{}.pickle'.format(fileName), 'rb') as f:
            return cPickle.load(f)

    def firstLearning(self):
        print("\n\nfirstLearning\n")
        df = self.loadFirstDF()
        df = self.filterColumns(df)
        df = self.filterRowsByResName(df)
        df = self.filterRwosByDistinctPairs(df)
        df = self.filterRowsByGroupSize(df)
        del df["pdb_code"]

        df = df.dropna(how="any")
        df = self.filterRowsByGroupSize(df)

        X = df.iloc[:,1:]
        y = df.iloc[:,0]
        clf = self.learnClfRandomForest(X,y)

        self.exportClf(clf, 'randomForest1')
        return clf

    def secondLearning(self):
        print("\n\nsecondLearning\n")
        df = self.loadFirstDF()
        df = self.filterColumns(df)
        df = self.filterRowsByResName(df)
        df = self.filterRwosByDistinctPairs(df)
        df = self.filterRowsByGroupSize(df)
        del df["pdb_code"]

        del df["res_name"]
        dfy = self.loadResNames()
        df.index = dfy.index
        df = pd.concat([dfy.loc[:,"res_name_group"], df], axis=1)
        df = df.dropna(how="any")

        X = df.iloc[:,1:]
        y = df.iloc[:,0]
        #clf = self.learnClfRandomForest(X,y)
        clf = self.importClf('randomForest2')

        self.exportClf(clf, 'randomForest2')
        return clf

    def firstTestLearning(self):
        print("\n\nfirstTestLearning\n")
        df = self.loadFirstDF()
        df = self.filterColumnsForTestData(df)
        df = self.filterRowsByResName(df)
        df = self.filterRwosByDistinctPairs(df)
        df = self.filterRowsByGroupSize(df)
        del df["pdb_code"]

        df = df.dropna(how="any")
        df = self.filterRowsByGroupSize(df)

        X = df.iloc[:,1:]
        y = df.iloc[:,0]
        clf = self.learnClfRandomForest(X,y)

        self.exportClf(clf, 'randomForestFirstTest')
        return clf

    # looks like secondLearning but doesn't save Classifier and uses filterColumnsForTestData instead of filterColumns
    def secondTestLearning(self):
        print("\n\nsecondTestLearning\n")
        df = self.loadFirstDF()
        df = self.filterColumnsForTestData(df)
        df = self.filterRowsByResName(df)
        df = self.filterRwosByDistinctPairs(df)
        df = self.filterRowsByGroupSize(df)
        del df["pdb_code"]

        del df["res_name"]
        dfy = self.loadResNames()
        df.index = dfy.index
        df = pd.concat([dfy.loc[:,"res_name_group"], df], axis=1)
        df = df.dropna(how="any")

        X = df.iloc[:,1:]
        y = df.iloc[:,0]
        clf = self.learnClfRandomForest(X,y)

        self.exportClf(clf, 'randomForesSecondTest')
        return clf

    def testFirstClassification(self):
        print("\n\ntestFirstClassification\n")
        df = self.loadTestDataDF()
        df = df.iloc[:,1:]
        df = self.filterColumnsForTestData(df)
        df = df.fillna(value=0)

        clf = self.importClf('randomForestFirstTest')
        print("**********************")
        result = clf.predict(df)
        self.saveTestClassification("outputFirst", result)

    def testSecondClassification(self):
        print("\n\ntestClassification\n")
        df = self.loadTestDataDF()
        df = df.iloc[:,1:]
        df = self.filterColumnsForTestData(df)
        df = df.fillna(value=0)

        clf = self.importClf('randomForesSecondTest')
        print("**********************")
        result = clf.predict(df)
        self.saveTestClassification("outputSecond", result)

mce1 = MyClassifierEngine()
#mce1.firstLearning()

mce2 = MyClassifierEngine()
#mce2.secondLearning()

mce3 = MyClassifierEngine()
mce3.firstTestLearning()

mce4 = MyClassifierEngine()
mce4.secondTestLearning()

mceTestFirst = MyClassifierEngine()
mceTestFirst.testFirstClassification()

mceTestSecond = MyClassifierEngine()
mceTestSecond.testSecondClassification()
