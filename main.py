import logging
from pydantic import BaseModel, Field, field_validator
from nicegui import ui
import plotly.graph_objects as go

logging.basicConfig(level=logging.INFO)

# ================= 1. CORE: Валидация & Математика =================
class MarketingParams(BaseModel):
    """Схема маркетинговых параметров (строгая валидация по Pydantic v2)"""
    budget: float = Field(default=10000.0, ge=0, description="Рекламный бюджет (₽)")
    cpc: float = Field(default=50.0, gt=0, description="Цена за клик (₽)")
    ctr: float = Field(default=2.0, ge=0, le=100, description="CTR (%)")
    funnel_conv: float = Field(default=5.0, ge=0, le=100, description="Конверсия в покупку (%)")

    @field_validator('budget', 'cpc')
    @classmethod
    def check_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Бюджет и CPC должны быть > 0")
        return v

def calculate_cac(p: MarketingParams) -> float:
    """Расчет Cost of Customer Acquisition по воронке"""
    clicks = p.budget / p.cpc
    leads = clicks * (p.ctr / 100)
    customers = leads * (p.funnel_conv / 100)
    return p.budget / max(customers, 1)  # защита от ZeroDivision

# ================= 2. UI: Реактивный NiceGUI Dashboard =================
ui.add_head_html('''<meta name="viewport" content="width=device-width, initial-scale=1">''')
ui.add_css('''
    body { font-family: system-ui, -apple-system, sans-serif; background: #f8f9fa; }
    .kpi-card { background: white; padding: 12px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); text-align: center; }
    .kpi-label { font-size: 0.75rem; color: #666; margin-bottom: 4px; }
    .kpi-value { font-size: 1.4rem; font-weight: 700; color: #1565c0; }
    .slider-row { width: 100%; max-width: 500px; margin: 16px auto; }
    .slider-label { font-weight: 600; margin-bottom: 4px; }
''')

# Состояние
params = MarketingParams()

# Fixed Header с KPI
with ui.header().classes('bg-white shadow-md px-4 py-2 w-full'):
    with ui.row().classes('w-full justify-around items-center'):
        ui.label('LTV').classes('kpi-label')
        ui.label('—').classes('kpi-value')        ui.label('CAC').classes('kpi-label')
        cac_display = ui.label('0.00 ₽').classes('kpi-value')
        ui.label('ROMI').classes('kpi-label')
        ui.label('—').classes('kpi-value')

ui.markdown('### 📊 Unit-Economy Simulator').style('text-align:center; margin: 12px 0 0;')

# Слайдеры ввода
def build_slider(label: str, mn: float, mx: float, step: float, init: float) -> tuple[ui.slider, ui.label]:
    with ui.column().classes('slider-row'):
        ui.label(label).classes('slider-label')
        sl = ui.slider(min=mn, max=mx, step=step, value=init).classes('w-full')
        val_label = ui.label(f'{init:g}').classes('text-center text-sm text-gray-600')
    return sl, val_label

sl_budget, lb_budget = build_slider('💰 Бюджет (₽)', 500, 100_000, 500, params.budget)
sl_cpc, lb_cpc = build_slider('🔗 CPC (₽)', 5, 500, 1, params.cpc)
sl_ctr, lb_ctr = build_slider('👁️ CTR (%)', 0.1, 25, 0.1, params.ctr)
sl_conv, lb_conv = build_slider('🎯 Конверсия (%)', 0.5, 30, 0.1, params.funnel_conv)

# График воронки (Plotly)
chart = ui.plotly().classes('w-full h-64 mt-4')

def update_dashboard():
    try:
        p = MarketingParams(
            budget=sl_budget.value,
            cpc=sl_cpc.value,
            ctr=sl_ctr.value,
            funnel_conv=sl_conv.value
        )
        cac = calculate_cac(p)
        cac_display.text = f'{cac:,.1f} ₽'

        lb_budget.text = f'{p.budget:,.0f}'
        lb_cpc.text = f'{p.cpc:.0f}'
        lb_ctr.text = f'{p.ctr:.1f}%'
        lb_conv.text = f'{p.funnel_conv:.1f}%'

        # Данные воронки
        clicks = p.budget / p.cpc
        leads = clicks * (p.ctr / 100)
        customers = leads * (p.funnel_conv / 100)

        fig = go.Figure(go.Bar(
            x=['Клики', 'Лиды', 'Покупки'],
            y=[clicks, leads, max(customers, 1)],
            marker_color=['#90caf9', '#42a5f5', '#1565c0'],
            text=[f'{clicks:,.0f}', f'{leads:,.0f}', f'{max(customers, 1):.0f}'],
            textposition='auto'        ))
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            height=220,
            showlegend=False,
            title='Воронка трафика (реактивный расчет)'
        )
        chart.figure = fig
    except Exception as e:
        cac_display.text = '⚠️ Ошибка'
        ui.notify(f'Валидация: {str(e)}', type='warning')

# Привязка реактивности
for sl in [sl_budget, sl_cpc, sl_ctr, sl_conv]:
    sl.on_value_change(lambda _: update_dashboard())

# Тестовая кнопка (Self-Check MVP)
def run_internal_tests():
    try:
        p = MarketingParams(budget=10000, cpc=50, ctr=2, funnel_conv=5)
        expected = 10000 / ((10000/50)*0.02*0.05)
        assert abs(calculate_cac(p) - expected) < 0.01
        p_zero = MarketingParams(budget=100, cpc=10, ctr=0.1, funnel_conv=0.1)
        assert calculate_cac(p_zero) > 0
        ui.notify('✅ Unit-тесты прошли успешно', type='positive')
    except Exception as e:
        ui.notify(f'❌ Тесты упали: {e}', type='negative')

ui.button('🧪 Запустить тесты', on_click=run_internal_tests).style('margin: 20px auto; display: block;')

# Инициализация
update_dashboard()

if __name__ == '__main__':
    # host='0.0.0.0' открывает доступ в мобильном браузере
    ui.run(host='0.0.0.0', port=8000, reload=False, title='UnitEco Simulator')
