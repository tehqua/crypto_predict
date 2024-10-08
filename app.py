
# Import các thư viện cần thiết
import streamlit as st
import requests
import plotly.graph_objs as go
import pandas as pd
from plotly.subplots import make_subplots
from statsmodels.tsa.statespace.sarimax import SARIMAX
from pmdarima.arima.utils import ndiffs
# Định nghĩa các hàm cần thiết

def get_crypto_prices():
    url = "https://api.binance.com/api/v3/ticker/price"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def get_crypto_history(symbol, interval='1d', limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def crypto_currency_overview():
    st.title("Crypto Price Viewer")

    crypto_prices = get_crypto_prices()
    crypto_symbols = [crypto['symbol'] for crypto in crypto_prices]

    selected_crypto = st.selectbox("Select Cryptocurrency", crypto_symbols)

    selected_interval = st.radio("Select Interval", ["1d", "1h", "1w", "1y"])

    if selected_crypto:
        st.write(f"### Real-time Prices for {selected_crypto}")
        st.write("Price (USDT)")
        for crypto in crypto_prices:
            if crypto['symbol'] == selected_crypto:
                st.write(crypto['price'])

        crypto_history = get_crypto_history(selected_crypto, interval=selected_interval)
        if crypto_history:
            df = pd.DataFrame(crypto_history, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # Kiểm tra và xử lý dữ liệu null
            if df.isnull().sum().any():
                st.warning("Missing values detected! Filling with mean values.")
                df.fillna(df.mean(), inplace=True)

            # Kiểm tra kiểu dữ liệu của cột 'close' và chuyển đổi sang kiểu dữ liệu số nếu cần
            if df['close'].dtype == 'object':
                df['close'] = pd.to_numeric(df['close'], errors='coerce')

            # Tiếp tục với phần SARIMA nếu có đủ dữ liệu
            if len(df) >= 100:
                # Chuyển đổi kiểu dữ liệu của cột 'volume' và 'taker_buy_base_asset_volume' sang số
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
                df['taker_buy_base_asset_volume'] = pd.to_numeric(df['taker_buy_base_asset_volume'], errors='coerce')

                st.subheader("Price Chart")
                # Get SARIMA forecast
                model, forecast_mean, forecast_conf_int = sarima_forecast(df['close'])

                # Plot historical data and forecast
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05)

                # Add price trace to subplot 1
                fig.add_trace(go.Scatter(x=df.index, y=df['close'], mode='lines', name='Price'), row=1, col=1)
                fig.update_yaxes(title_text="Price (USDT)", row=1, col=1)

                # Add forecast mean to subplot 1
                fig.add_trace(go.Scatter(x=forecast_mean.index, y=forecast_mean, mode='lines', name='Forecast', line=dict(dash='dash')), row=1, col=1)

                # Add prediction interval to subplot 1
                fig.add_trace(go.Scatter(x=forecast_conf_int.index,
                                         y=forecast_conf_int.iloc[:, 0],
                                         mode='lines',
                                         line=dict(color='grey'),
                                         showlegend=False), row=1, col=1)
                fig.add_trace(go.Scatter(x=forecast_conf_int.index,
                                         y=forecast_conf_int.iloc[:, 1],
                                         mode='lines',
                                         line=dict(color='grey'),
                                         fill='tonexty',
                                         fillcolor='rgba(0,100,80,0.2)',
                                         showlegend=False), row=1, col=1)

                # Add volume trace to subplot 2
                volume_color = ['green' if buy_volume > sell_volume else 'red' for buy_volume, sell_volume in zip(df['taker_buy_base_asset_volume'], df['volume'] - df['taker_buy_base_asset_volume'])]
                fig.add_trace(go.Bar(x=df.index, y=df['volume'], name='Volume', marker_color=volume_color), row=2, col=1)
                fig.update_yaxes(title_text="Volume", row=2, col=1)

                fig.update_layout(title=f"Price and Volume Chart for {selected_crypto}", height=600)

                st.plotly_chart(fig)
            else:
                st.error("Insufficient data for SARIMA analysis.")


def sarima_forecast(series, forecast_period=30, alpha=0.05):
    # Xác định số lần cần thực hiện sai phân bằng kiểm tra ADF
    d = ndiffs(series, test='adf')

    # Khởi tạo mô hình SARIMA với số lần sai phân đã xác định
    model = SARIMAX(series, order=(1, d, 1), seasonal_order=(1, d, 1, 12))
    
    # Khớp mô hình với dữ liệu
    model_fit = model.fit(disp=False)
    
    # Dự đoán với số bước tiến trình cần dự đoán
    forecast = model_fit.get_forecast(steps=forecast_period)
    
    # Lấy giá trị dự đoán trung bình
    forecast_mean = forecast.predicted_mean
    
    # Lấy khoảng tin cậy của dự đoán
    forecast_conf_int = forecast.conf_int(alpha=alpha)
    
    return model_fit, forecast_mean, forecast_conf_int


def main():
    # Tiêu đề của ứng dụng
    st.title("Crypto Analysis App")

    # Lựa chọn trang
    page = st.sidebar.selectbox("Select Page", ["Crypto Currency Overview"])

    # Chạy trang tương ứng với lựa chọn
    if page == "Crypto Currency Overview":
        crypto_currency_overview()

# Chạy ứng dụng
if __name__ == "__main__":
    main()
