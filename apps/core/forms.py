"""Small public calculators with explicit, non-binding results."""

from decimal import Decimal, ROUND_UP

from django import forms


class SolarEstimatorForm(forms.Form):
    """Collect the minimum inputs for an educational sizing conversation."""

    monthly_kwh = forms.DecimalField(min_value=Decimal("1"), max_digits=9, decimal_places=1, label="Average monthly energy use (kWh)")
    peak_load_kw = forms.DecimalField(min_value=Decimal("0.1"), max_digits=7, decimal_places=2, label="Peak load to support (kW)")
    backup_hours = forms.DecimalField(min_value=Decimal("0.5"), max_value=Decimal("48"), max_digits=5, decimal_places=1, label="Backup time required (hours)")
    solar_hours = forms.DecimalField(min_value=Decimal("2"), max_value=Decimal("8"), initial=Decimal("4.5"), max_digits=3, decimal_places=1, label="Usable solar hours per day")

    def recommendation(self) -> dict[str, Decimal]:
        """Return rounded planning values without representing them as a quote."""
        data = self.cleaned_data
        solar_kw = (data["monthly_kwh"] / Decimal("30") / data["solar_hours"] * Decimal("1.25")).quantize(Decimal("0.1"), rounding=ROUND_UP)
        inverter_kw = (data["peak_load_kw"] * Decimal("1.30")).quantize(Decimal("0.1"), rounding=ROUND_UP)
        battery_kwh = (data["peak_load_kw"] * data["backup_hours"] * Decimal("1.20")).quantize(Decimal("0.1"), rounding=ROUND_UP)
        return {"solar_kw": solar_kw, "inverter_kw": inverter_kw, "battery_kwh": battery_kwh}
