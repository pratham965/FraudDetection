import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sklearn.metrics import confusion_matrix, precision_score, recall_score
import io
from utils import filter_data, process_data, calculate_metrics, get_time_granularity

# Set page configuration
st.set_page_config(
    page_title="Fraud Analysis Dashboard",
    page_icon="🔍",
    layout="wide"
)

# Initialize session state for filters
if 'data' not in st.session_state:
    st.session_state.data = None
if 'date_range' not in st.session_state:
    st.session_state.date_range = None
if 'payer_id' not in st.session_state:
    st.session_state.payer_id = None
if 'payee_id' not in st.session_state:
    st.session_state.payee_id = None
if 'transaction_id' not in st.session_state:
    st.session_state.transaction_id = ""
if 'metrics_date_range' not in st.session_state:
    st.session_state.metrics_date_range = None

# Header
st.title("Fraud Analysis Dashboard")

# Data Upload Section
st.header("Data Upload")
uploaded_file = st.file_uploader("Upload your transaction data (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # Load data based on file type
        if uploaded_file.name.endswith('.csv'):
            data = pd.read_csv(uploaded_file)
        else:
            data = pd.read_excel(uploaded_file)

        # Process data to ensure it has required columns
        data = process_data(data)

        # Store in session state
        st.session_state.data = data

        # Display success message
        st.success(f"Successfully loaded data with {len(data)} transactions")

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.info(
            "Make sure your data contains the required columns: Transaction_ID, Timestamp, Payer_ID, Payee_ID, is_fraud_predicted, is_fraud_reported, Transaction_Channel, Transaction_Payment_Mode, Payment_Gateway_Bank, and Amount")

# Main dashboard content
if st.session_state.data is not None:
    data = st.session_state.data

    # Get min and max dates for filters
    min_date = pd.to_datetime(data['Timestamp']).min().date()
    max_date = pd.to_datetime(data['Timestamp']).max().date()

    # Sidebar for filters
    st.sidebar.header("Filters")

    # Date range filter
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if len(date_range) == 2:
        st.session_state.date_range = date_range

    # Payer ID filter
    payer_ids = sorted(data['Payer_ID'].unique().tolist())
    selected_payer = st.sidebar.multiselect(
        "Filter by Payer ID",
        options=payer_ids,
        default=None
    )
    st.session_state.payer_id = selected_payer if selected_payer else None

    # Payee ID filter
    payee_ids = sorted(data['Payee_ID'].unique().tolist())
    selected_payee = st.sidebar.multiselect(
        "Filter by Payee ID",
        options=payee_ids,
        default=None
    )
    st.session_state.payee_id = selected_payee if selected_payee else None

    # Transaction ID search
    transaction_id = st.sidebar.text_input("Search by Transaction ID", value=st.session_state.transaction_id)
    st.session_state.transaction_id = transaction_id

    # Apply filters
    filtered_data = filter_data(
        data,
        date_range=st.session_state.date_range,
        payer_id=st.session_state.payer_id,
        payee_id=st.session_state.payee_id,
        transaction_id=st.session_state.transaction_id
    )

    # Stats overview
    st.header("Overview Statistics")

    # Create three columns for key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Transactions", len(filtered_data))

    with col2:
        predicted_fraud_count = filtered_data['is_fraud_predicted'].sum()
        predicted_fraud_pct = (predicted_fraud_count / len(filtered_data)) * 100 if len(filtered_data) > 0 else 0
        st.metric("Predicted Frauds", f"{predicted_fraud_count} ({predicted_fraud_pct:.2f}%)")

    with col3:
        reported_fraud_count = filtered_data['is_fraud_reported'].sum()
        reported_fraud_pct = (reported_fraud_count / len(filtered_data)) * 100 if len(filtered_data) > 0 else 0
        st.metric("Reported Frauds", f"{reported_fraud_count} ({reported_fraud_pct:.2f}%)")

    with col4:
        total_amount = filtered_data['Amount'].sum()
        st.metric("Total Transaction Amount", f"${total_amount:,.2f}")

    # Transaction data table
    st.header("Transaction Data")

    # Format data for display
    display_data = filtered_data.copy()
    display_data['Timestamp'] = pd.to_datetime(display_data['Timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    display_data['Amount'] = display_data['Amount'].apply(lambda x: f"${x:,.2f}")
    display_data['is_fraud_predicted'] = display_data['is_fraud_predicted'].apply(lambda x: '✅' if x else '❌')
    display_data['is_fraud_reported'] = display_data['is_fraud_reported'].apply(lambda x: '✅' if x else '❌')

    # Display table with pagination
    st.dataframe(display_data, use_container_width=True)

    # Time Series Analysis
    st.header("Time Series Analysis")

    # Time frame selector
    time_frame = st.selectbox(
        "Select Time Frame",
        options=["Last 7 days", "Last 30 days", "Last 90 days", "Last year", "All time"],
        index=4  # Default to "All time"
    )

    # Calculate time series data based on selection
    if time_frame != "All time":
        if time_frame == "Last 7 days":
            cutoff_date = max_date - timedelta(days=7)
        elif time_frame == "Last 30 days":
            cutoff_date = max_date - timedelta(days=30)
        elif time_frame == "Last 90 days":
            cutoff_date = max_date - timedelta(days=90)
        else:  # Last year
            cutoff_date = max_date - timedelta(days=365)

        time_series_data = filtered_data[pd.to_datetime(filtered_data['Timestamp']).dt.date >= cutoff_date]
    else:
        time_series_data = filtered_data

    if len(time_series_data) > 0:
        # Determine time granularity based on time frame
        granularity = get_time_granularity(time_frame)

        # Group by time and count frauds
        time_series_data['Timestamp'] = pd.to_datetime(time_series_data['Timestamp'])

        if granularity == 'D':
            time_series_data['TimeBucket'] = time_series_data['Timestamp'].dt.date
            x_title = "Date"
        elif granularity == 'W':
            time_series_data['TimeBucket'] = time_series_data['Timestamp'].dt.to_period('W').apply(
                lambda x: x.start_time.date())
            x_title = "Week Starting"
        elif granularity == 'M':
            time_series_data['TimeBucket'] = time_series_data['Timestamp'].dt.to_period('M').apply(
                lambda x: x.start_time.date())
            x_title = "Month"
        else:  # 'H' - hourly
            time_series_data['TimeBucket'] = time_series_data['Timestamp'].dt.floor('H')
            x_title = "Hour"

        # Aggregate by time bucket
        time_agg = time_series_data.groupby('TimeBucket').agg(
            total_transactions=('Transaction_ID', 'count'),
            predicted_frauds=('is_fraud_predicted', 'sum'),
            reported_frauds=('is_fraud_reported', 'sum')
        ).reset_index()

        # Create time series plot
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=time_agg['TimeBucket'],
            y=time_agg['total_transactions'],
            mode='lines',
            name='Total Transactions',
            line=dict(color='blue', width=2)
        ))

        fig.add_trace(go.Scatter(
            x=time_agg['TimeBucket'],
            y=time_agg['predicted_frauds'],
            mode='lines',
            name='Predicted Frauds',
            line=dict(color='orange', width=2)
        ))

        fig.add_trace(go.Scatter(
            x=time_agg['TimeBucket'],
            y=time_agg['reported_frauds'],
            mode='lines',
            name='Reported Frauds',
            line=dict(color='red', width=2)
        ))

        fig.update_layout(
            title='Transaction and Fraud Trends Over Time',
            xaxis_title=x_title,
            yaxis_title='Count',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data available for the selected time frame.")

    # Fraud Comparison Graphs
    st.header("Fraud Pattern Analysis")

    # Create tabs for different comparisons
    tabs = st.tabs([
        "Transaction Channel",
        "Payment Mode",
        "Gateway Bank",
        "Payer Analysis",
        "Payee Analysis"
    ])

    # Tab 1: Transaction Channel Analysis
    with tabs[0]:
        if len(filtered_data) > 0:
            # Group by Transaction Channel
            channel_data = filtered_data.groupby('Transaction_Channel').agg(
                total=('Transaction_ID', 'count'),
                predicted_frauds=('is_fraud_predicted', 'sum'),
                reported_frauds=('is_fraud_reported', 'sum')
            ).reset_index()

            # Calculate percentages
            channel_data['predicted_fraud_pct'] = (
                        channel_data['predicted_frauds'] / channel_data['total'] * 100).round(2)
            channel_data['reported_fraud_pct'] = (channel_data['reported_frauds'] / channel_data['total'] * 100).round(
                2)

            # Create comparison bar chart
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=channel_data['Transaction_Channel'],
                y=channel_data['predicted_fraud_pct'],
                name='Predicted Fraud %',
                marker_color='orange'
            ))

            fig.add_trace(go.Bar(
                x=channel_data['Transaction_Channel'],
                y=channel_data['reported_fraud_pct'],
                name='Reported Fraud %',
                marker_color='red'
            ))

            fig.update_layout(
                title='Fraud Percentage by Transaction Channel',
                xaxis_title='Transaction Channel',
                yaxis_title='Percentage (%)',
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Display data table
            st.subheader("Transaction Channel Data")
            channel_display = channel_data.copy()
            channel_display['predicted_fraud_pct'] = channel_display['predicted_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            channel_display['reported_fraud_pct'] = channel_display['reported_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            st.dataframe(channel_display, use_container_width=True)
        else:
            st.warning("No data available for analysis.")

    # Tab 2: Payment Mode Analysis
    with tabs[1]:
        if len(filtered_data) > 0:
            # Group by Payment Mode
            payment_mode_data = filtered_data.groupby('Transaction_Payment_Mode').agg(
                total=('Transaction_ID', 'count'),
                predicted_frauds=('is_fraud_predicted', 'sum'),
                reported_frauds=('is_fraud_reported', 'sum')
            ).reset_index()

            # Calculate percentages
            payment_mode_data['predicted_fraud_pct'] = (
                        payment_mode_data['predicted_frauds'] / payment_mode_data['total'] * 100).round(2)
            payment_mode_data['reported_fraud_pct'] = (
                        payment_mode_data['reported_frauds'] / payment_mode_data['total'] * 100).round(2)

            # Create comparison bar chart
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=payment_mode_data['Transaction_Payment_Mode'],
                y=payment_mode_data['predicted_fraud_pct'],
                name='Predicted Fraud %',
                marker_color='orange'
            ))

            fig.add_trace(go.Bar(
                x=payment_mode_data['Transaction_Payment_Mode'],
                y=payment_mode_data['reported_fraud_pct'],
                name='Reported Fraud %',
                marker_color='red'
            ))

            fig.update_layout(
                title='Fraud Percentage by Payment Mode',
                xaxis_title='Payment Mode',
                yaxis_title='Percentage (%)',
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Display data table
            st.subheader("Payment Mode Data")
            payment_display = payment_mode_data.copy()
            payment_display['predicted_fraud_pct'] = payment_display['predicted_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            payment_display['reported_fraud_pct'] = payment_display['reported_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            st.dataframe(payment_display, use_container_width=True)
        else:
            st.warning("No data available for analysis.")

    # Tab 3: Gateway Bank Analysis
    with tabs[2]:
        if len(filtered_data) > 0:
            # Group by Gateway Bank
            bank_data = filtered_data.groupby('Payment_Gateway_Bank').agg(
                total=('Transaction_ID', 'count'),
                predicted_frauds=('is_fraud_predicted', 'sum'),
                reported_frauds=('is_fraud_reported', 'sum')
            ).reset_index()

            # Calculate percentages
            bank_data['predicted_fraud_pct'] = (bank_data['predicted_frauds'] / bank_data['total'] * 100).round(2)
            bank_data['reported_fraud_pct'] = (bank_data['reported_frauds'] / bank_data['total'] * 100).round(2)

            # Create comparison bar chart
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=bank_data['Payment_Gateway_Bank'],
                y=bank_data['predicted_fraud_pct'],
                name='Predicted Fraud %',
                marker_color='orange'
            ))

            fig.add_trace(go.Bar(
                x=bank_data['Payment_Gateway_Bank'],
                y=bank_data['reported_fraud_pct'],
                name='Reported Fraud %',
                marker_color='red'
            ))

            fig.update_layout(
                title='Fraud Percentage by Payment Gateway Bank',
                xaxis_title='Gateway Bank',
                yaxis_title='Percentage (%)',
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Display data table
            st.subheader("Gateway Bank Data")
            bank_display = bank_data.copy()
            bank_display['predicted_fraud_pct'] = bank_display['predicted_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            bank_display['reported_fraud_pct'] = bank_display['reported_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            st.dataframe(bank_display, use_container_width=True)
        else:
            st.warning("No data available for analysis.")

    # Tab 4: Payer Analysis
    with tabs[3]:
        if len(filtered_data) > 0:
            # Group by Payer ID
            payer_data = filtered_data.groupby('Payer_ID').agg(
                total=('Transaction_ID', 'count'),
                predicted_frauds=('is_fraud_predicted', 'sum'),
                reported_frauds=('is_fraud_reported', 'sum'),
                total_amount=('Amount', 'sum')
            ).reset_index()

            # Calculate percentages
            payer_data['predicted_fraud_pct'] = (payer_data['predicted_frauds'] / payer_data['total'] * 100).round(2)
            payer_data['reported_fraud_pct'] = (payer_data['reported_frauds'] / payer_data['total'] * 100).round(2)

            # Sort by total transactions
            payer_data = payer_data.sort_values('total', ascending=False).head(10)

            # Create comparison bar chart
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=payer_data['Payer_ID'],
                y=payer_data['predicted_fraud_pct'],
                name='Predicted Fraud %',
                marker_color='orange'
            ))

            fig.add_trace(go.Bar(
                x=payer_data['Payer_ID'],
                y=payer_data['reported_fraud_pct'],
                name='Reported Fraud %',
                marker_color='red'
            ))

            fig.update_layout(
                title='Fraud Percentage by Top 10 Payers (by transaction count)',
                xaxis_title='Payer ID',
                yaxis_title='Percentage (%)',
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Display data table
            st.subheader("Top Payer Data")
            payer_display = payer_data.copy()
            payer_display['predicted_fraud_pct'] = payer_display['predicted_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            payer_display['reported_fraud_pct'] = payer_display['reported_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            payer_display['total_amount'] = payer_display['total_amount'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(payer_display, use_container_width=True)
        else:
            st.warning("No data available for analysis.")

    # Tab 5: Payee Analysis
    with tabs[4]:
        if len(filtered_data) > 0:
            # Group by Payee ID
            payee_data = filtered_data.groupby('Payee_ID').agg(
                total=('Transaction_ID', 'count'),
                predicted_frauds=('is_fraud_predicted', 'sum'),
                reported_frauds=('is_fraud_reported', 'sum'),
                total_amount=('Amount', 'sum')
            ).reset_index()

            # Calculate percentages
            payee_data['predicted_fraud_pct'] = (payee_data['predicted_frauds'] / payee_data['total'] * 100).round(2)
            payee_data['reported_fraud_pct'] = (payee_data['reported_frauds'] / payee_data['total'] * 100).round(2)

            # Sort by total transactions
            payee_data = payee_data.sort_values('total', ascending=False).head(10)

            # Create comparison bar chart
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=payee_data['Payee_ID'],
                y=payee_data['predicted_fraud_pct'],
                name='Predicted Fraud %',
                marker_color='orange'
            ))

            fig.add_trace(go.Bar(
                x=payee_data['Payee_ID'],
                y=payee_data['reported_fraud_pct'],
                name='Reported Fraud %',
                marker_color='red'
            ))

            fig.update_layout(
                title='Fraud Percentage by Top 10 Payees (by transaction count)',
                xaxis_title='Payee ID',
                yaxis_title='Percentage (%)',
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            # Display data table
            st.subheader("Top Payee Data")
            payee_display = payee_data.copy()
            payee_display['predicted_fraud_pct'] = payee_display['predicted_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            payee_display['reported_fraud_pct'] = payee_display['reported_fraud_pct'].apply(lambda x: f"{x:.2f}%")
            payee_display['total_amount'] = payee_display['total_amount'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(payee_display, use_container_width=True)
        else:
            st.warning("No data available for analysis.")

    # Evaluation Metrics Section
    st.header("Fraud Detection Evaluation Metrics")

    # Metrics date range filter
    st.subheader("Select Time Period for Metrics")
    metrics_date_range = st.date_input(
        "Metrics Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="metrics_date_range_selector"
    )

    if len(metrics_date_range) == 2:
        st.session_state.metrics_date_range = metrics_date_range

        # Filter data for metrics
        metrics_data = data.copy()
        if st.session_state.metrics_date_range is not None:
            start_date, end_date = st.session_state.metrics_date_range
            metrics_data = metrics_data[
                (pd.to_datetime(metrics_data['Timestamp']).dt.date >= start_date) &
                (pd.to_datetime(metrics_data['Timestamp']).dt.date <= end_date)
                ]

        if len(metrics_data) > 0:
            # Calculate metrics
            y_true = metrics_data['is_fraud_reported'].astype(int)
            y_pred = metrics_data['is_fraud_predicted'].astype(int)

            # Confusion matrix
            cm = confusion_matrix(y_true, y_pred)
            tn, fp, fn, tp = cm.ravel()

            # Create confusion matrix figure
            cm_fig = px.imshow(
                cm,
                labels=dict(x="Predicted", y="Actual", color="Count"),
                x=['Not Fraud', 'Fraud'],
                y=['Not Fraud', 'Fraud'],
                text_auto=True,
                color_continuous_scale='Reds'
            )

            cm_fig.update_layout(
                title='Confusion Matrix',
                xaxis_title='Predicted Label',
                yaxis_title='Actual Label'
            )

            # Calculate performance metrics
            precision = precision_score(y_true, y_pred, zero_division=0)
            recall = recall_score(y_true, y_pred, zero_division=0)
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            accuracy = (tp + tn) / (tp + tn + fp + fn)

            # Display metrics in two columns
            col1, col2 = st.columns(2)

            with col1:
                st.plotly_chart(cm_fig, use_container_width=True)

            with col2:
                st.subheader("Performance Metrics")
                metrics_df = pd.DataFrame({
                    'Metric': ['Accuracy', 'Precision', 'Recall', 'F1 Score'],
                    'Value': [accuracy, precision, recall, f1],
                    'Description': [
                        'Overall correct predictions',
                        'Percentage of predicted frauds that were actual frauds',
                        'Percentage of actual frauds that were correctly predicted',
                        'Harmonic mean of precision and recall'
                    ]
                })

                # Format metrics as percentages
                metrics_df['Value'] = metrics_df['Value'].apply(lambda x: f"{x * 100:.2f}%")

                st.dataframe(metrics_df, use_container_width=True, hide_index=True)

                # Detailed counts
                st.subheader("Detailed Counts")
                counts_df = pd.DataFrame({
                    'Metric': ['True Positives (TP)', 'False Positives (FP)', 'True Negatives (TN)',
                               'False Negatives (FN)'],
                    'Count': [tp, fp, tn, fn],
                    'Description': [
                        'Correctly predicted frauds',
                        'Incorrectly predicted as fraud',
                        'Correctly predicted as not fraud',
                        'Missed actual frauds'
                    ]
                })

                st.dataframe(counts_df, use_container_width=True, hide_index=True)
        else:
            st.warning("No data available for the selected time period.")

    # Download section
    st.header("Export Data")

    if len(filtered_data) > 0:
        # Create a download button for the filtered data
        csv = filtered_data.to_csv(index=False)

        st.download_button(
            label="Download Filtered Data as CSV",
            data=csv,
            file_name="fraud_analysis_data.csv",
            mime="text/csv"
        )
else:
    # Show welcome message and instructions when no data is loaded
    st.info("Welcome to the Fraud Analysis Dashboard. Please upload your transaction data to begin.")

    st.markdown("""
    ### Required Data Format

    Your data should include the following columns:
    - Transaction_ID: Unique identifier for each transaction
    - Timestamp: Date and time of the transaction
    - Payer_ID: ID of the entity making the payment
    - Payee_ID: ID of the entity receiving the payment
    - is_fraud_predicted: Boolean indicating if the system flagged the transaction as fraud (0 or 1)
    - is_fraud_reported: Boolean indicating if the transaction was actually reported as fraud (0 or 1)
    - Transaction_Channel: Channel used for the transaction (e.g., Mobile, Web, POS)
    - Transaction_Payment_Mode: Payment method (e.g., Credit Card, Debit Card, UPI)
    - Payment_Gateway_Bank: Bank processing the payment
    - Amount: Transaction amount

    Upload a CSV or Excel file with these columns to analyze your fraud detection performance.
    """)
