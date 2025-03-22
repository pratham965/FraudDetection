import numpy as np
import matplotlib.pyplot as plt
from tensorflow.keras.models import load_model

# Load the trained model (Ensure model.h5 exists or retrain if needed)
model = load_model("model.h5")  

# Load or prepare test data (Ensure x_non_fraud_test and df_fraud are available)
# Replace with actual data loading if needed
x_non_fraud_test = np.load("x_non_fraud_test.npy")
df_fraud = np.load("df_fraud.npy")

# Predict reconstructed outputs
x_non_fraud_pred = model.predict(x_non_fraud_test)
df_fraud_pred = model.predict(df_fraud)

# Compute RMSE for non-fraud test set
recon_error_non_fraud = np.sqrt(np.mean((x_non_fraud_test - x_non_fraud_pred) ** 2, axis=1))

# Compute RMSE for fraud set
recon_error_fraud = np.sqrt(np.mean((df_fraud - df_fraud_pred) ** 2, axis=1))

# Set threshold (Mean + 3*Std) from non-fraud data
threshold = np.mean(recon_error_non_fraud) + 3 * np.std(recon_error_non_fraud)

# Flag anomalies in fraud data
anomalies = recon_error_fraud > threshold

# Print results
print(f"Anomaly Threshold: {threshold}")
print(f"Number of detected anomalies: {np.sum(anomalies)} out of {len(anomalies)} fraud samples")

# Plot reconstruction error distributions
plt.figure(figsize=(10, 5))
plt.hist(recon_error_non_fraud, bins=50, alpha=0.7, label="Non-Fraud")
plt.hist(recon_error_fraud, bins=50, alpha=0.7, label="Fraud")
plt.axvline(threshold, color='red', linestyle='dashed', linewidth=2, label="Threshold")
plt.xlabel("Reconstruction Error (RMSE)")
plt.ylabel("Count")
plt.title("Reconstruction Error Distribution")
plt.legend()
plt.show()
