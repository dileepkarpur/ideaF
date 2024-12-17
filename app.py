from flask import Flask, render_template, jsonify, request, send_from_directory
import yfinance as yf
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)

# Configuration
LLMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"

def safe_float(value):
    """Convert value to float safely, return None if not possible"""
    try:
        if pd.isna(value):
            return None
        return float(value)
    except:
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/api/stock/<ticker>', methods=['GET'])
def get_stock_data(ticker):
    try:
        # Get stock information using yfinance
        stock = yf.Ticker(ticker)
        
        # Get current price info
        info = stock.info
        print("Stock Info Keys:", info.keys())  # Debug print
        
        # Try different price fields
        current_price = (
            safe_float(info.get('currentPrice')) or
            safe_float(info.get('regularMarketPrice')) or
            safe_float(info.get('lastPrice')) or
            safe_float(info.get('price'))
        )
        
        previous_close = (
            safe_float(info.get('previousClose')) or
            safe_float(info.get('regularMarketPreviousClose'))
        )
        
        if current_price and previous_close:
            price_change = ((current_price - previous_close) / previous_close) * 100
        else:
            price_change = None
            
        # Get shares outstanding for EPS calculation
        shares_outstanding = (
            safe_float(info.get('sharesOutstanding')) or
            safe_float(info.get('shares')) or
            safe_float(info.get('marketCap') / current_price if current_price else None)
        )
        print(f"Shares Outstanding: {shares_outstanding}")
            
        # Get EPS values
        eps = (
            safe_float(info.get('trailingEPS')) or
            safe_float(info.get('forwardEPS'))
        )
        
        # Get quarterly financial data
        income_stmt = stock.quarterly_income_stmt
        balance = stock.quarterly_balance_sheet
        
        print("Income Statement Columns:", income_stmt.columns)
        print("Income Statement Index:", income_stmt.index)
        
        if income_stmt.empty:
            return jsonify({'error': f'No financial data found for ticker {ticker}'}), 404

        # Process the financial data
        quarterly_data = []
        
        # Get the last 4 quarters of data
        for date in income_stmt.columns[:4]:
            # Extract metrics carefully
            try:
                revenue = safe_float(income_stmt.loc['Total Revenue', date] if 'Total Revenue' in income_stmt.index else None)
                net_income = safe_float(income_stmt.loc['Net Income', date] if 'Net Income' in income_stmt.index else None)
                
                # Try alternative field names if the main ones aren't found
                if revenue is None:
                    revenue = safe_float(income_stmt.loc['Revenue', date] if 'Revenue' in income_stmt.index else None)
                
                if net_income is None:
                    net_income = safe_float(income_stmt.loc['Net Income Common Stockholders', date] if 'Net Income Common Stockholders' in income_stmt.index else None)
                
                # Get balance sheet metrics
                total_assets = safe_float(balance.loc['Total Assets', date] if 'Total Assets' in balance.index else None)
                total_liabilities = safe_float(balance.loc['Total Liabilities', date] if 'Total Liabilities' in balance.index else None)
                
                quarter_data = {
                    'date': date.strftime('%Y-%m-%d'),
                    'metrics': {
                        'Revenue': revenue,
                        'NetIncome': net_income,
                        'Assets': total_assets,
                        'Liabilities': total_liabilities,
                    }
                }
                
                # Calculate EPS if we have net income and shares outstanding
                if net_income and shares_outstanding:
                    calculated_eps = net_income / shares_outstanding
                    print(f"Calculated EPS: NetIncome ({net_income}) / Shares ({shares_outstanding}) = {calculated_eps}")
                    quarter_data['metrics']['EPS'] = calculated_eps
                elif 'trailingEPS' in info:
                    print(f"Using trailingEPS from yfinance: {info['trailingEPS']}")
                    quarter_data['metrics']['EPS'] = safe_float(info['trailingEPS'])
                else:
                    print("Could not calculate or fetch EPS")                # Calculate Profit Margin if possible
                if revenue and net_income and revenue != 0:
                    quarter_data['metrics']['ProfitMargin'] = (net_income / revenue) * 100
                
                quarterly_data.append(quarter_data)
                
            except Exception as e:
                print(f"Error processing quarter {date}: {str(e)}")
                continue

        # Get company information
        company_info = {
            'name': info.get('longName', ticker),
            'ticker': ticker,
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'description': info.get('longBusinessSummary', 'N/A'),
            'marketCap': safe_float(info.get('marketCap')),
            'employees': info.get('fullTimeEmployees', 'N/A'),
            'currentPrice': current_price,
            'previousClose': previous_close,
            'priceChange': price_change,
            'eps': eps,
            'lastUpdated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Print debug information
        print("Processed Data:", json.dumps({
            'company_info': company_info,
            'quarterly_data': quarterly_data
        }, indent=2))

        return jsonify({
            'company_info': company_info,
            'quarterly_data': quarterly_data
        })

    except Exception as e:
        print(f"Error in get_stock_data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_financials():
    try:
        data = request.json
        latest = data['quarterly_data'][0]['metrics']

        # Safely get financial values with defaults
        market_cap = safe_float(data['company_info'].get('marketCap')) or 0
        current_price = safe_float(data['company_info'].get('currentPrice')) or 0
        revenue = safe_float(latest.get('Revenue')) or 0
        net_income = safe_float(latest.get('NetIncome')) or 0
        eps = safe_float(latest.get('EPS')) or 0
        profit_margin = safe_float(latest.get('ProfitMargin')) or 0
        assets = safe_float(latest.get('Assets')) or 0
        liabilities = safe_float(latest.get('Liabilities')) or 0

        prompt = f"""Analyze the following quarterly financial data for {data['company_info']['name']} ({data['company_info']['ticker']}):

Company Information:
- Sector: {data['company_info']['sector']}
- Industry: {data['company_info']['industry']}
- Market Cap: ${market_cap:,.2f}
- Current Price: ${current_price:,.2f}

Latest Quarter Financials ({data['quarterly_data'][0]['date']}):
- Revenue: ${revenue:,.2f}
- Net Income: ${net_income:,.2f}
- EPS: ${eps:,.2f}
- Profit Margin: {profit_margin:.2f}%
- Total Assets: ${assets:,.2f}
- Total Liabilities: ${liabilities:,.2f}

Provide a detailed analysis"""

        response = requests.post(
            LLMSTUDIO_URL,
            json={
                "messages": [
                    {"role": "system", "content": "You are a financial analyst providing detailed company analysis."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 300
            }
        )

        if response.status_code == 200:
            return jsonify({'analysis': response.json()['choices'][0]['message']['content']})
        else:
            return jsonify({'error': "Error generating analysis"}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict', methods=['POST'])
def predict_financials():
    try:
        data = request.json
        quarters = data['quarterly_data']

        # Calculate growth rates
        revenue_growth = []
        income_growth = []
        margin_trend = []

        for i in range(len(quarters) - 1):
            current = quarters[i]['metrics']
            previous = quarters[i + 1]['metrics']
            
            if current.get('Revenue') and previous.get('Revenue'):
                growth = ((current['Revenue'] - previous['Revenue']) / previous['Revenue']) * 100
                revenue_growth.append(growth)
            
            if current.get('NetIncome') and previous.get('NetIncome'):
                growth = ((current['NetIncome'] - previous['NetIncome']) / previous['NetIncome']) * 100
                income_growth.append(growth)
            
            if current.get('ProfitMargin') and previous.get('ProfitMargin'):
                margin_trend.append(current['ProfitMargin'] - previous['ProfitMargin'])

        prompt = f"""Based on the historical quarterly data for {data['company_info']['name']} ({data['company_info']['ticker']}):

Company Context:
- Sector: {data['company_info']['sector']}
- Industry: {data['company_info']['industry']}
- Market Cap: ${data['company_info'].get('marketCap', 0):,.2f}
- Current Price: ${data['company_info'].get('currentPrice', 0):,.2f}

Historical Performance (Last 4 Quarters):
Dates: {[q['date'] for q in quarters]}
Revenue: {[f"${q['metrics'].get('Revenue', 0):,.2f}" for q in quarters]}
Net Income: {[f"${q['metrics'].get('NetIncome', 0):,.2f}" for q in quarters]}
Profit Margins: {[f"{q['metrics'].get('ProfitMargin', 0):,.2f}%" for q in quarters]}

Growth Metrics:
- Revenue Growth Rates: {[f"{g:.2f}%" for g in revenue_growth]}
- Net Income Growth Rates: {[f"{g:.2f}%" for g in income_growth]}
- Margin Trends: {[f"{m:+.2f}%" for m in margin_trend]}

Provide detailed predictions for the next quarter in a summary format:
1. Revenue Range Forecast
2. Net Income Projection
3. Expected Profit Margin
4. EPS Estimate
5. Key Growth Drivers
6. Potential Challenges

Include:
- Market conditions impact
- Industry trends
- Company-specific factors
- Confidence level in predictions
- Key metrics to watch"""

        response = requests.post(
            LLMSTUDIO_URL,
            json={
                "messages": [
                    {"role": "system", "content": "You are a financial analyst making data-driven predictions."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 300
            }
        )

        if response.status_code == 200:
            return jsonify({'prediction': response.json()['choices'][0]['message']['content']})
        else:
            return jsonify({'error': "Error generating prediction"}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/risk', methods=['POST'])
def assess_risk():
    try:
        data = request.json
        latest = data['quarterly_data'][0]['metrics']
        
        # Safely get financial values with defaults
        market_cap = safe_float(data['company_info'].get('marketCap')) or 0
        current_price = safe_float(data['company_info'].get('currentPrice')) or 0
        revenue = safe_float(latest.get('Revenue')) or 0
        net_income = safe_float(latest.get('NetIncome')) or 0
        profit_margin = safe_float(latest.get('ProfitMargin')) or 0
        assets = safe_float(latest.get('Assets')) or 0
        liabilities = safe_float(latest.get('Liabilities')) or 0
        
        # Calculate risk metrics
        debt_to_assets = (liabilities / assets * 100) if assets and liabilities and assets != 0 else None

        prompt = f"""Assess risks for {data['company_info']['name']} ({data['company_info']['ticker']}):

Company Context:
- Sector: {data['company_info']['sector']}
- Industry: {data['company_info']['industry']}
- Market Cap: ${market_cap:,.2f}
- Current Price: ${current_price:,.2f}
- Employees: {data['company_info']['employees']}

Financial Position (Latest Quarter {data['quarterly_data'][0]['date']}):
- Revenue: ${revenue:,.2f}
- Net Income: ${net_income:,.2f}
- Profit Margin: {profit_margin:.2f}%
- Total Assets: ${assets:,.2f}
- Total Liabilities: ${liabilities:,.2f}
- Debt to Assets Ratio: {f"{debt_to_assets:.2f}%" if debt_to_assets is not None else "N/A"}

Provide a comprehensive risk assessment covering:
1. Financial Risks
   - Liquidity risk
   - Credit risk
   - Capital structure risk

2. Market Risks
   - Competition analysis
   - Market share threats
   - Industry disruption risks

3. Operational Risks
   - Supply chain
   - Labor/workforce
   - Technology dependencies

4. Strategic Risks
   - Business model sustainability
   - Growth strategy risks
   - Market positioning

5. External Risks
   - Regulatory environment
   - Economic factors
   - Geopolitical risks

Include specific risk ratings (Low/Medium/High) for each category."""

        response = requests.post(
            LLMSTUDIO_URL,
            json={
                "messages": [
                    {"role": "system", "content": "You are a risk analyst providing comprehensive risk assessments."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 300
            }
        )

        if response.status_code == 200:
            return jsonify({'risk_assessment': response.json()['choices'][0]['message']['content']})
        else:
            return jsonify({'error': "Error generating risk assessment"}), 500

    except Exception as e:
        print(f"Error in assess_risk: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
