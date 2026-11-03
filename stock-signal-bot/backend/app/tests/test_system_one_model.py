from app.ai.system_one import decision_engine


def test_system_one_model_uses_live_price_structure_and_volume_context():
    result = decision_engine.evaluate(
        symbol='RELIANCE',
        price=1568.4,
        vwap=1549.0,
        rsi=62,
        ema_9=1578.0,
        ema_21=1548.5,
        atr=21.4,
        change_pct=1.8,
        news_sentiment='BULLISH',
        market_phase='MORNING_SESSION',
        adx=28,
        relative_volume=1.7,
        support=1540.0,
        resistance=1590.0,
        trend_strength=0.74,
        volume_confirmation=True,
        structure_bias='BULLISH',
        market_regime='TRENDING'
    )

    assert result['ai_score'] >= 0.72
    assert result['ai_verdict'] in {'STRONG_BUY_CONFLUENCE', 'MODERATE_BUY'}
    assert 'Price is holding above VWAP with strong trend confirmation' in result['system_one_rules']
    assert 'Volume surge confirms participation' in result['system_one_rules']
