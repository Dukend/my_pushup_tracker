"""
formatters.py — reusable text formatters for bot messages.
"""

from __future__ import annotations


def progress_bar(current: int, goal: int) -> str:
    pct = min(int(current / goal * 100), 100) if goal else 0
    fill = pct // 10
    return f"[{'█' * fill}{'░' * (10 - fill)}] {pct}%"


def fmt_stats(today: int, total: int, goal: int, streak: int, record: int) -> str:
    done = today >= goal
    return (
        f"📊 <b>Статистика</b>\n\n"
        f"📅 Сегодня:  <b>{today}</b> / {goal}  {'✅' if done else ''}\n"
        f"🏋 Всего:    <b>{total}</b>\n"
        f"🔥 Стрик:    <b>{streak}</b> дн. подряд\n"
        f"🏆 Рекорд:   <b>{record}</b> за день\n\n"
        f"{progress_bar(today, goal)}"
    )


def fmt_add(
    n: int, today: int, total: int, goal: int, new_record: bool, just_reached: bool
) -> str:
    text = (
        f"✅ +{n} отжиманий\n\n"
        f"📅 Сегодня: <b>{today}</b> / {goal}\n"
        f"🏋 Всего:   <b>{total}</b>\n\n"
        f"{progress_bar(today, goal)}"
    )
    if new_record:
        text += "\n\n🏆 <b>Новый рекорд дня!</b>"
    if just_reached:
        text += "\n\n🎯 <b>Цель дня выполнена!</b>"
    return text


def fmt_history(history: list[tuple[str, int]], goal: int) -> str:
    lines = []
    for i, (d, val) in enumerate(history):
        mark = "✅" if val >= goal else "·"
        bar = "▓" * min(val // 10, 15)
        label = "сегодня" if i == len(history) - 1 else f"-{len(history) - 1 - i}д"
        lines.append(f"{mark} <code>{d} ({label:>7}): {val:4} {bar}</code>")
    return "📅 <b>Последние 7 дней</b>\n\n" + "\n".join(lines)


def fmt_reminders(reminders: dict) -> str:
    if not reminders:
        return "⏰ Напоминаний нет."
    lines = []
    for r in reminders.values():
        icon = "✅" if r["enabled"] else "🔕"
        lines.append(f"{icon} <b>{r['label']}</b>: {r['time']}")
    return "⏰ <b>Напоминания</b>\n\n" + "\n".join(lines)
