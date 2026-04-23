"""
retrain.py — Run this once if you get numpy/_pickle errors loading models.
Usage:  python retrain.py
"""
import pandas as pd, numpy as np, pickle, json
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split

df = pd.read_csv('./data/crop_data.csv')
df['State_Name'] = df['State_Name'].str.strip()
df['Crop']       = df['Crop'].str.strip()
df['soil_type']  = df['soil_type'].str.strip()
df['Season']     = df['Season'].str.strip()
df = df.dropna()

le_state  = LabelEncoder()
le_crop   = LabelEncoder()
le_soil   = LabelEncoder()
le_season = LabelEncoder()

df['state_enc']  = le_state.fit_transform(df['State_Name'])
df['crop_enc']   = le_crop.fit_transform(df['Crop'])
df['soil_enc']   = le_soil.fit_transform(df['soil_type'])
df['season_enc'] = le_season.fit_transform(df['Season'])

X_crop = df[['state_enc','soil_enc','season_enc','Area']]
y_crop = df['crop_enc']
Xtr, Xte, ytr, yte = train_test_split(X_crop, y_crop, test_size=0.2, random_state=42)
rf_crop = RandomForestClassifier(n_estimators=100, random_state=42)
rf_crop.fit(Xtr, ytr)
print(f'Crop accuracy: {rf_crop.score(Xte, yte):.4f}')

X_yield = df[['state_enc','crop_enc','season_enc','soil_enc','Area']]
y_yield = df['Production'] / df['Area']
Xtr2, Xte2, ytr2, yte2 = train_test_split(X_yield, y_yield, test_size=0.2, random_state=42)
rf_yield = RandomForestRegressor(n_estimators=100, random_state=42)
rf_yield.fit(Xtr2, ytr2)
print(f'Yield R2: {rf_yield.score(Xte2, yte2):.4f}')

encoders = {'state': le_state, 'crop': le_crop, 'soil': le_soil, 'season': le_season}
for name, obj in [('crop_model', rf_crop), ('yield_model', rf_yield), ('encoders', encoders)]:
    with open(f'./models/{name}.pkl', 'wb') as f:
        pickle.dump(obj, f, protocol=4)
    print(f'Saved {name}.pkl')

meta = {'states': list(le_state.classes_), 'crops': list(le_crop.classes_),
        'soils': list(le_soil.classes_), 'seasons': list(le_season.classes_)}
with open('./models/model_meta.json', 'w', encoding='utf-8') as f:
    json.dump(meta, f)
print('Models rebuilt successfully!')
