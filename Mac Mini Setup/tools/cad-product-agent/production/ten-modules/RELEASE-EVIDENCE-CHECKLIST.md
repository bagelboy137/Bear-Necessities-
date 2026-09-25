# Release evidence checklist

Complete separately for BN-M01 through BN-M10. The framework must reject release
when any required cell is blank or linked evidence is missing.

## Common frame evidence

- [ ] Approved payload, longitudinal/lateral/vertical load cases and safety factor
- [ ] Supplier cut-tolerance and direct-fulfillment terms accepted in writing
- [ ] Incoming inspection report for sample frame kit
- [ ] Released joint architecture and BOM—external 4132/3393 or internal AF-010,
      never both
- [ ] Assembly drawing, torque table and work instructions
- [ ] Static proof-load report
- [ ] Handle-cycle report
- [ ] Vibration/road and fastener-retention report
- [ ] Vehicle anchor installation and retention evidence
- [ ] Corrosion/material compatibility review

## Module evidence

- [ ] Every BOM row is orderable or has a released custom drawing and supplier
- [ ] No `SOURCE_REQUIRED`, `CUSTOM_REQUIRED`, `ENGINEERING_HOLD` or rejected
      positive-quantity row remains
- [ ] Purchased-component manufacturer drawing and revision archived
- [ ] Static six-face, moving, service and installation envelopes pass
- [ ] Native multi-component Fusion interference report passes
- [ ] STEP, native CAD, drawing PDF/DXF, BOM and revision manifest archived
- [ ] Module-specific physical tests from `PHYSICAL-TEST-PLAN.md` pass
- [ ] Labels, warnings, instructions and service/inspection intervals approved
- [ ] Packaging/drop test and one real direct-to-customer shipment pass
- [ ] Independent human reviewer signs job and manually sets `RELEASED`

## Mandatory release metadata

```text
Module ID:
Revision:
Released BOM hash:
Released CAD hash:
Released drawing hash:
Supplier evidence path:
Physical test evidence path:
Reviewer name:
Reviewer signature/date:
```

No local or cloud model may fill reviewer identity/signature or transition a job
to `RELEASED`.
