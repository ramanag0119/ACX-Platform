import { MeterHierarchyView } from "../components/MeterHierarchyView";
import { useMeterFilters, useMeterHierarchy } from "../data/useMeterHierarchy";

/**
 * Power View: the same Building -> Floor -> Room -> Appliance drill-down as
 * Energy View, over the same live reads, with the card figures switched to
 * load. Both come from `device_param` `active_power`, whose unit really is KW:
 * the left figure sums the devices in scope, the bold figure is the highest
 * single device in it.
 *
 * The reads themselves, and the gaps in them, are documented in
 * `../data/useMeterHierarchy`.
 */
const PowerView = () => {
  const { scope, filters } = useMeterFilters();
  const hierarchy = useMeterHierarchy(scope);

  return (
    <MeterHierarchyView
      title="Power View"
      metric="power"
      hierarchy={hierarchy}
      filters={filters}
    />
  );
};

export default PowerView;
