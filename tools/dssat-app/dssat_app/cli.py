"""Interfaz de linea de comandos de dssat-app.

Ejemplos::

    # Inspeccionar un FileX
    dssat-app info UFGA8201.MZX

    # Barrido de fecha de siembra y densidad, modo seasonal (N)
    dssat-app sweep UFGA8201.MZX --crop maize --trt 1 \\
        --factor pdate=82030,82057,82084 --factor ppop=6,7.2,8.5 \\
        --mode N --out ./_run --dssat-dir /opt/dssat

El subcomando ``sweep`` requiere un ejecutable de CSM; ``info`` y ``batch`` no.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from . import batch as batch_mod
from .crops import CROPS, RUN_MODES, crop_by_filex_ext, get_crop
from .filex import FACTORS, FileX
from .sweep import Sweep


def _parse_factor(spec: str):
    """'pdate=82030,82057' -> ('pdate', ['82030','82057'])."""
    if "=" not in spec:
        raise argparse.ArgumentTypeError(
            f"Factor mal formado: '{spec}'. Use clave=v1,v2,..."
        )
    key, values = spec.split("=", 1)
    return key.strip(), [v.strip() for v in values.split(",") if v.strip()]


def cmd_info(args) -> int:
    fx = FileX.read(args.filex)
    print(f"FileX: {args.filex}")
    print(f"Secciones: {', '.join(fx.section_names())}")
    print("\nTratamientos:")
    for t in fx.treatments():
        n = t.get("N", "?")
        name = next((v for k, v in t.items() if k.upper().startswith("TNAME")), "")
        print(f"  {n:>3}  {name}")
    print("\nFactores de barrido disponibles:")
    for key, f in FACTORS.items():
        print(f"  {key:<8} {f.label_es}  [{f.section} -> {f.column}]")
    return 0


def cmd_batch(args) -> int:
    crop = get_crop(args.crop) if args.crop else crop_by_filex_ext(
        Path(args.filex).suffix)
    model = args.model or crop.default_model
    trts: List[int] = [int(x) for x in args.trt.split(",")]
    entries = [batch_mod.BatchEntry(filex=Path(args.filex).name, trtno=t,
                                    sq=(1 if args.mode == "Q" else 0))
               for t in trts]
    path = batch_mod.write_batch(args.out, entries, crop.name_es, model,
                                 args.mode)
    print(f"Batch escrito en {path}")
    return 0


def cmd_sweep(args) -> int:
    sweep = Sweep(args.filex, crop=args.crop, model=args.model, trtno=args.trt)
    for key, values in (args.factor or []):
        sweep.add_factor(key, values)

    if args.design_only:
        design = sweep.build(args.out)
        print(design.to_frame().to_string(index=False))
        return 0

    result = sweep.run(args.out, mode=args.mode, dssat_dir=args.dssat_dir,
                       extra_inputs=args.input or [], timeout=args.timeout)
    if not result.run.ok:
        print(f"CSM devolvio codigo {result.run.returncode}", file=sys.stderr)
        if result.run.error_out:
            print("ERROR.OUT:\n" + result.run.error_out, file=sys.stderr)
    print(result.table.to_string(index=False))
    csv = Path(args.out) / "sweep_resultados.csv"
    result.table.to_csv(csv, index=False)
    print(f"\nResultados guardados en {csv}")
    return 0 if result.run.ok else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dssat-app", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("info", help="Inspeccionar un FileX")
    pi.add_argument("filex")
    pi.set_defaults(func=cmd_info)

    pb = sub.add_parser("batch", help="Generar un DSSBatch.v48")
    pb.add_argument("filex")
    pb.add_argument("--crop", choices=list(CROPS))
    pb.add_argument("--model")
    pb.add_argument("--trt", default="1", help="tratamientos, ej. 1,2,3")
    pb.add_argument("--mode", default="B", choices=list(RUN_MODES))
    pb.add_argument("--out", default="DSSBatch.v48")
    pb.set_defaults(func=cmd_batch)

    ps = sub.add_parser("sweep", help="Barrido de parametros (sensibilidad)")
    ps.add_argument("filex")
    ps.add_argument("--crop", choices=list(CROPS), required=True)
    ps.add_argument("--model")
    ps.add_argument("--trt", type=int, default=1)
    ps.add_argument("--factor", type=_parse_factor, action="append",
                    help="clave=v1,v2,... (repetible)")
    ps.add_argument("--mode", default="N", choices=["N", "Q", "B"])
    ps.add_argument("--out", default="./_run")
    ps.add_argument("--dssat-dir", dest="dssat_dir")
    ps.add_argument("--input", action="append", help="archivo de insumo a copiar (repetible)")
    ps.add_argument("--timeout", type=float)
    ps.add_argument("--design-only", action="store_true",
                    help="solo generar variantes y mostrar el diseno")
    ps.set_defaults(func=cmd_sweep)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
