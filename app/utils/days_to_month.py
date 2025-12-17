from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


def days_to_str(days, start_date=None):
    """
    Функция для конвертации дней в строку
    """
    if start_date:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = start_date + timedelta(days=days)
        difference = relativedelta(end_date, start_date)
        months = difference.years * 12 + difference.months
        remaining_days = difference.days
    else:
        months = int(days // 30.44)
        remaining_days = int(round(days % 30.44))

    month_forms = ['месяц', 'месяца', 'месяцев']
    day_forms = ['день', 'дня', 'дней']

    def get_plural(number, forms):
        if number % 10 == 1 and number % 100 != 11:
            return forms[0]
        elif 2 <= number % 10 <= 4 and (number % 100 < 10 or number % 100 >= 20):
            return forms[1]
        else:
            return forms[2]

    parts = []
    if months > 0:
        parts.append(f"{months if remaining_days < 29 else months+1} {get_plural(months, month_forms)}")
    if remaining_days > 1 and remaining_days < 29:
        parts.append(f"{remaining_days} {get_plural(remaining_days, day_forms)}")

    return " и ".join(parts) if parts else ""
