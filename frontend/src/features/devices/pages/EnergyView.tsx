import { MeterHierarchyView } from "../components/MeterHierarchyView";
import { useMeterFilters, useMeterHierarchy } from "../data/useMeterHierarchy";

/**
 * Energy View: the Building -> Floor -> Room -> Appliance drill-down over the
 * live HMS reads. The bold figure on each card is consumed energy from
 * `energy_stat`, which stores no unit -- so none is shown.
 *
 * The reads themselves, and the gaps in them, are documented in
 * `../data/useMeterHierarchy`.
 */
const EnergyView = () => {
  const { scope, filters } = useMeterFilters();
  const hierarchy = useMeterHierarchy(scope);

  return (
    <MeterHierarchyView
      title="Energy View"
      metric="energy"
      hierarchy={hierarchy}
      filters={filters}
    />
  );
};

export default EnergyView;
