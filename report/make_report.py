"""Generate a two-page Proof-of-Service PDF from three validated runs."""
import argparse
from datetime import datetime
from io import BytesIO
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fpdf import FPDF
from matplotlib.figure import Figure
import numpy as np
import config
from twin.analyze import analyze_run, compare_phases, savings_estimate
from twin.data import DataError, expand_paths, read_run
from twin.fit_tau import FitError, fit_tau, twin_overlay
from twin.normalization import fit_weather_model


class ServicePDF(FPDF):
    def __init__(self, fake):
        super().__init__()
        self.fake = fake
        self.set_margins(16, 16, 16)
        self.set_auto_page_break(True, margin=20)

    def header(self):
        if self.fake:
            with self.rotation(35, 105, 145):
                self.set_font("Helvetica", "B", 64)
                self.set_text_color(242, 228, 220)
                self.set_xy(20, 125)
                self.cell(170, 24, "FAKE DATA", align="C")
        self.set_fill_color(18, 42, 60)
        self.rect(0, 0, 210, 9, style="F")
        self.set_xy(16, 16)
        self.set_text_color(18, 42, 60)
        self.set_font("Helvetica", "B", 11)
        self.cell(120, 7, "CLIMATWIN / TEAM TRIANGLE")
        self.set_font("Helvetica", "", 9)
        self.cell(58, 7, "SOFTWARE DEMO" if self.fake else "RECORDED RUNS", align="R")
        self.ln(12)

    def footer(self):
        self.set_y(-14)
        self.set_text_color(95, 109, 120)
        self.set_font("Helvetica", "", 8)
        label = "FAKE / simulated readings - not hardware evidence" if self.fake else "Cooling-performance proxy - no measured power"
        self.cell(150, 5, label)
        self.cell(28, 5, f"{self.page_no()} / {{nb}}", align="R")

    def heading(self, text):
        self.set_x(16)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(0, 113, 115)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")

    def paragraph(self, text, size=10):
        self.set_x(16)
        self.set_font("Helvetica", "", size)
        self.set_text_color(40, 56, 68)
        self.multi_cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def grid(self, headers, rows, widths):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(226, 240, 240)
        self.set_text_color(18, 42, 60)
        for values, header in [(headers, True)] + [(r, False) for r in rows]:
            self.set_x(16)
            self.set_font("Helvetica", "B" if header else "", 9)
            for width, value in zip(widths, values):
                self.cell(width, 8, str(value), border="B", fill=header)
            self.ln(8)
        self.ln(3)


def fmt(value, digits=2):
    return "unknown" if value is None else f"{value:.{digits}f}"


def build_report(paths, *, kw=None, tariff=None, target=26.0, setpoint=None,
                 weather_baselines=()):
    paths = list(map(Path, paths))
    records = [analyze_run(p, setpoint) for p in paths]
    comparison = compare_phases(records)
    by_phase = {r["phase"]: r for r in records}
    order = [by_phase[p] for p in ("clean1", "blocked", "clean2")]
    frames = {str(read_run(p).phase.iloc[0]): read_run(p) for p in paths}
    fits = {phase: fit_tau(df) for phase, df in frames.items()}
    estimate = savings_estimate(by_phase["blocked"], by_phase["clean2"], kw=kw, tariff=tariff, target=target)
    weather_text = "Unavailable: need at least two independent BEFORE-service (blocked) runs at distinct outdoor temperatures. These three phases alone cannot establish weather normalization."
    if weather_baselines:
        training_paths = list(map(Path, weather_baselines))
        if len({p.resolve() for p in training_paths}) != len(training_paths):
            raise ValueError("Weather training files must be distinct independent recordings.")
        training = [analyze_run(p) for p in training_paths]
        if any(r["phase"] != "blocked" or r["synthetic"] != order[0]["synthetic"] for r in training):
            raise ValueError("Report weather training must use before-service blocked runs of matching provenance.")
        model = fit_weather_model(training)
        outdoor_now = by_phase["clean2"]["outdoor_mean_C"]
        if outdoor_now is None:
            raise ValueError("Recovery run has no outdoor temperature for normalization.")
        expected = model.predict(outdoor_now)
        normalized = (expected - fits["clean2"].tau_min) / expected * 100
        weather_text = (f"Normalized reduction in tau: {normalized:.1f}%. Expected old-condition tau "
                        f"{expected:.2f} min at {outdoor_now:.1f} C; actual {fits['clean2'].tau_min:.2f} min. "
                        f"Linear model from {model.n_runs} before-service runs spanning {model.min_C:.1f}-{model.max_C:.1f} C. "
                        "Small demonstration only; not validated across seasons.")
    pdf = ServicePDF(fake=order[0]["synthetic"])
    pdf.alias_nb_pages()
    pdf.set_title("ClimaTwin Proof-of-Service - " + ("FAKE demo" if pdf.fake else "recorded runs"))
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 25)
    pdf.cell(0, 13, "Proof of Service", new_x="LMARGIN", new_y="NEXT")
    pdf.paragraph("Before / blocked filter / recovery comparison | " + datetime.now().astimezone().isoformat(timespec="minutes"), 9)
    raw = comparison["raw_improvement_pct"]
    pdf.heading(f"Raw cooling-time improvement: {raw:.1f}%")
    pdf.paragraph(f"'Cooling {raw:.1f}% faster' denotes a reduction in the fitted time constant: "
                  "(tau_blocked - tau_clean2) / tau_blocked x 100. It is not a measured electrical efficiency gain.")
    pdf.heading("01 / Conditions and fitted performance")
    pdf.grid(["Phase", "Outdoor C", "Start C", "Setpoint C", "Tau min", "R2"],
             [[r["phase"], fmt(r["outdoor_mean_C"], 1), fmt(r["start_C"], 1),
               fmt(r["setpoint_C"], 1), fmt(r["tau_min"]), fmt(r["r2"], 3)] for r in order],
             [28, 33, 29, 34, 29, 25])
    pdf.paragraph("Start = fitted temperature at detected cooling onset. Setpoint is operator-supplied. "
                  "Outdoor values are window means from Open-Meteo or a typed fallback; consult logger sidecars for provenance.", 8)
    pdf.heading("02 / Room response against the clean twin")
    figure = Figure(figsize=(8.5, 3.8), layout="constrained")
    axis = figure.subplots()
    for phase, color in (("clean1", "#007f83"), ("blocked", "#d97538"), ("clean2", "#597baf")):
        df, fit = frames[phase], fits[phase]
        view = df[(df.elapsed_min >= fit.start_min) & (df.elapsed_min <= fit.start_min + 15)]
        axis.plot(view.elapsed_min - fit.start_min, view.room_C, color=color, label=phase, linewidth=1.4)
    blocked_df = frames["blocked"]
    view = blocked_df[(blocked_df.elapsed_min >= fits["blocked"].start_min) &
                      (blocked_df.elapsed_min <= fits["blocked"].start_min + 15)]
    axis.plot(view.elapsed_min - fits["blocked"].start_min,
              twin_overlay(fits["clean1"], fits["blocked"], view.elapsed_min), "--",
              color="#172f43", label="clean twin / blocked start", linewidth=2)
    axis.set(xlabel="Minutes since detected cooling start", ylabel="Room temperature (C)")
    axis.grid(alpha=0.18)
    axis.legend(fontsize=8, ncol=2)
    chart = BytesIO()
    figure.savefig(chart, format="png", dpi=160)
    chart.seek(0)
    pdf.image(chart, x=16, w=178)
    pdf.ln(3)
    pdf.paragraph(f"Clean-run repeatability: {comparison['clean_repeatability_pct']:.1f}% tau difference. "
                  + comparison["decision"], 9)

    pdf.add_page()
    pdf.heading("03 / Raw versus weather-normalized comparison")
    pdf.paragraph(f"Raw reduction in tau: {raw:.1f}%. " + weather_text)
    outdoor_values = [value for r in order for value in (r["outdoor_min_C"], r["outdoor_max_C"]) if value is not None]
    pdf.paragraph((f"Observed outdoor range: {min(outdoor_values):.1f}-{max(outdoor_values):.1f} C. " if outdoor_values
                   else "Outdoor temperature unavailable. ") +
                  "A narrow range cannot demonstrate robustness to weather changes. Weather-adjusted values are never invented.")
    pdf.heading("04 / Estimated energy and rupee impact")
    if estimate["available"]:
        pdf.paragraph(f"Estimated impact per pull-down: Rs {estimate['estimated_rs']:.2f} "
                      f"({estimate['estimated_kwh']:.3f} kWh). Negative values indicate an increase in cost.")
        pdf.paragraph(f"Common start {estimate['common_start_C']:.2f} C to target {target:.2f} C: "
                      f"before {estimate['before_minutes']:.2f} min, after {estimate['after_minutes']:.2f} min, "
                      f"saved {estimate['minutes_saved']:.2f} min. Calculation: minutes saved / 60 x "
                      f"{kw:g} kW x Rs {tariff:g}/kWh. {estimate['assumptions']}")
    else:
        pdf.paragraph("Not calculated. " + estimate["reason"])
    pdf.paragraph("The submitted deck showed a plug-in meter. It was dropped for safety and time. "
                  "Energy is estimated; this prototype measures temperature and humidity only.", 9)
    pdf.heading("05 / Supporting signals and fit quality")
    pdf.grid(["Phase", "Return - supply (C)", "RH drop (% points/min)"],
             [[r["phase"], fmt(r["temperature_split_C"]), fmt(r["humidity_drop_pct_per_min"], 3)] for r in order],
             [30, 70, 78])
    pdf.paragraph("Model: T(t) = T_final + (T0 - T_final) exp(-t/tau). Fit uses a 3-sample median and "
                  "the first 15 minutes of detected cooling; R2 must be >= 0.90. Tau is a cooling proxy, "
                  "not COP or a diagnosis. Temperature split can rise or fall with restricted airflow.", 9)
    pdf.paragraph("Alert default: health = min(100, 100 x tau_clean1 / tau_now); below 80 for three "
                  "consecutive 60-second fits. Threshold remains provisional until real runs support calibration. "
                  "Inverter cycling, occupancy, solar gain and humidity can confound the model.", 9)
    pdf.heading("06 / Source recordings")
    for record in order:
        pdf.paragraph(record["file"], 8)
    return bytes(pdf.output())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kw", type=float, default=config.AC_NAMEPLATE_KW)
    parser.add_argument("--tariff", type=float, default=config.TARIFF_RS_PER_KWH)
    parser.add_argument("--target-c", type=float, default=26)
    parser.add_argument("--setpoint-c", type=float, default=config.SETPOINT_C)
    parser.add_argument("--weather-baselines", nargs="*", default=[])
    args = parser.parse_args()
    try:
        content = build_report(expand_paths(args.files), kw=args.kw, tariff=args.tariff,
                               target=args.target_c, setpoint=args.setpoint_c,
                               weather_baselines=expand_paths(args.weather_baselines))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(content)
        print(f"Report saved: {args.output}")
    except (DataError, FitError, ValueError, OSError) as exc:
        parser.exit(1, f"Report not generated: {exc}\n")


if __name__ == "__main__":
    main()
