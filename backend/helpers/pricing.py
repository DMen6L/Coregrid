def calculate_floor_price(purchase_price: int, margin_percent: int) -> int:
    return (purchase_price * (100 + margin_percent) + 99) // 100
