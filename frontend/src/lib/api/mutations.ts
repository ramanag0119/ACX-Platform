/**
 * React Query mutations for every write endpoint.
 *
 * The invariant this file exists to enforce: after a successful mutation the
 * affected queries are INVALIDATED and refetched, so what the screen shows is
 * what PostgreSQL now holds -- never a locally patched copy. That is why a
 * browser refresh shows the same thing the UI showed a moment earlier.
 *
 * Errors are surfaced through the shared toast with `describeApiError`, so a
 * 409 ("that room is already allocated") reads the same everywhere.
 */

import { useMutation, useQueryClient, type UseMutationOptions } from "@tanstack/react-query";

import { toast } from "@/hooks/use-toast";
import { ApiError, describeApiError } from "./client";
import * as writes from "./writes";

/** Query key prefixes each domain touches, so invalidation stays honest. */
const INVALIDATE = {
  users: ["users", "roles", "departments", "job-functions", "auth"],
  roles: ["roles", "permissions", "modules", "auth"],
  departments: ["departments", "users"],
  jobFunctions: ["job-functions", "users"],
  serviceRequests: ["service-requests", "service-statuses", "daily-data-points"],
  serviceCatalogue: ["service-categories", "service-items", "service-types"],
  stays: ["stays", "occupancy", "rooms", "invoices", "daily-data-points"],
  occupancy: ["occupancy", "rooms", "amenity-conditions", "amenity-statuses"],
  devices: ["devices", "device-types", "incidents", "alerts"],
  firmware: ["firmware", "devices"],
  incidents: ["incidents", "alerts"],
  limitConfigs: ["limit-configs", "value-alerts"],
  facility: ["facilities", "rooms", "buildings", "floors", "properties"],
  catalogue: ["amenity-types", "packages", "features", "rooms"],
  offers: ["offers"],
  events: ["events"],
  holidays: ["holidays"],
  // A planned service touches its own list plus the rooms it takes out of
  // service, which is what `under_maintenance` does to occupancy.
  maintenance: ["maintenance-requests", "occupancy", "rooms"],
  // A job order names rooms and devices but changes neither, so only its own
  // list needs refetching.
  jobOrders: ["job-orders"],
} as const;

type Keys = readonly string[];

interface Options<TVars, TData> {
  /** Shown once the database has confirmed the change. */
  success?: string | ((data: TData, vars: TVars) => string);
  /** Extra query prefixes to refetch. */
  also?: Keys;
  onDone?: (data: TData, vars: TVars) => void;
}

/**
 * The one mutation factory. Every hook below is built from it, so success
 * toasts, error toasts and invalidation behave identically across the app.
 */
function useApiMutation<TVars, TData>(
  fn: (vars: TVars) => Promise<TData>,
  keys: Keys,
  options: Options<TVars, TData> = {},
  extra?: Omit<UseMutationOptions<TData, ApiError, TVars>, "mutationFn">,
) {
  const queryClient = useQueryClient();
  return useMutation<TData, ApiError, TVars>({
    mutationFn: fn,
    onSuccess: (data, vars) => {
      const prefixes = [...keys, ...(options.also ?? [])];
      for (const prefix of prefixes) {
        // Prefix match: ["stays", {...params}] is invalidated by ["stays"].
        queryClient.invalidateQueries({ queryKey: [prefix] });
      }
      const message =
        typeof options.success === "function" ? options.success(data, vars) : options.success;
      if (message) toast({ title: message });
      options.onDone?.(data, vars);
    },
    onError: (error) => {
      toast({
        title: "Could not save",
        description: describeApiError(error),
        variant: "destructive",
      });
    },
    ...extra,
  });
}

// ---------------------------------------------------------------------------
// Users, roles, departments, job functions
// ---------------------------------------------------------------------------

export const useCreateUser = (opts?: Options<writes.UserWrite, unknown>) =>
  useApiMutation(writes.createUser, INVALIDATE.users, { success: "Employee created", ...opts });

export const useUpdateUser = (
  opts?: Options<{ id: string; body: Partial<writes.UserWrite> }, unknown>,
) =>
  useApiMutation(
    ({ id, body }: { id: string; body: Partial<writes.UserWrite> }) => writes.updateUser(id, body),
    INVALIDATE.users,
    { success: "Employee updated", ...opts },
  );

export const useSetUserPassword = () =>
  useApiMutation(
    ({ id, password }: { id: string; password: string }) => writes.setUserPassword(id, password),
    INVALIDATE.users,
    { success: "Password updated" },
  );

export const useDeactivateUser = () =>
  useApiMutation((id: string) => writes.deactivateUser(id), INVALIDATE.users, {
    success: "Employee deactivated",
  });

export const useReactivateUser = () =>
  useApiMutation((id: string) => writes.reactivateUser(id), INVALIDATE.users, {
    success: "Employee reactivated",
  });

export const useCreateRole = (opts?: Options<writes.RoleWrite, unknown>) =>
  useApiMutation(writes.createRole, INVALIDATE.roles, { success: "Role created", ...opts });

export const useUpdateRole = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Partial<writes.RoleWrite> }) => writes.updateRole(id, body),
    INVALIDATE.roles,
    { success: "Role updated" },
  );

export const useReplaceRolePermissions = () =>
  useApiMutation(
    ({ id, permissions }: { id: string; permissions: writes.PermissionEntry[] }) =>
      writes.replaceRolePermissions(id, permissions),
    INVALIDATE.roles,
    { success: "Module permissions saved" },
  );

export const useCreateDepartment = (opts?: Options<string, unknown>) =>
  useApiMutation(writes.createDepartment, INVALIDATE.departments, {
    success: "Department created",
    ...opts,
  });

export const useUpdateDepartment = () =>
  useApiMutation(
    ({ id, name }: { id: string; name: string }) => writes.updateDepartment(id, name),
    INVALIDATE.departments,
    { success: "Department updated" },
  );

export const useCreateJobFunction = (opts?: Options<string, unknown>) =>
  useApiMutation(writes.createJobFunction, INVALIDATE.jobFunctions, {
    success: "Function created",
    ...opts,
  });

export const useUpdateJobFunction = () =>
  useApiMutation(
    ({ id, name }: { id: string; name: string }) => writes.updateJobFunction(id, name),
    INVALIDATE.jobFunctions,
    { success: "Function updated" },
  );

// ---------------------------------------------------------------------------
// Service requests and catalogue
// ---------------------------------------------------------------------------

export const useCreateServiceRequest = (opts?: Options<writes.ServiceRequestWrite, unknown>) =>
  useApiMutation(writes.createServiceRequest, INVALIDATE.serviceRequests, {
    success: "Service request raised",
    ...opts,
  });

export const useUpdateServiceRequest = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Parameters<typeof writes.updateServiceRequest>[1] }) =>
      writes.updateServiceRequest(id, body),
    INVALIDATE.serviceRequests,
    { success: "Service request updated" },
  );

export const useCancelServiceRequest = () =>
  useApiMutation(
    ({ id, reason }: { id: string; reason?: string | null }) =>
      writes.cancelServiceRequest(id, reason),
    INVALIDATE.serviceRequests,
    { success: "Service request cancelled" },
  );

export const useCreateServiceCategory = (opts?: Options<writes.ServiceCategoryWrite, unknown>) =>
  useApiMutation(writes.createServiceCategory, INVALIDATE.serviceCatalogue, {
    success: "Category created",
    ...opts,
  });

export const useUpdateServiceCategory = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Partial<writes.ServiceCategoryWrite> }) =>
      writes.updateServiceCategory(id, body),
    INVALIDATE.serviceCatalogue,
    { success: "Category updated" },
  );

export const useCreateServiceItem = (opts?: Options<writes.ServiceItemWrite, unknown>) =>
  useApiMutation(writes.createServiceItem, INVALIDATE.serviceCatalogue, {
    success: "Item created",
    ...opts,
  });

export const useUpdateServiceItem = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Partial<writes.ServiceItemWrite> }) =>
      writes.updateServiceItem(id, body),
    INVALIDATE.serviceCatalogue,
    { success: "Item updated" },
  );

// ---------------------------------------------------------------------------
// Stays
// ---------------------------------------------------------------------------

export const useCreateStay = (opts?: Options<writes.StayWrite, unknown>) =>
  useApiMutation(writes.createStay, INVALIDATE.stays, { success: "Booking created", ...opts });

export const useUpdateStay = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Partial<writes.StayWrite> }) => writes.updateStay(id, body),
    INVALIDATE.stays,
    { success: "Booking updated" },
  );

export const useCheckInStay = () =>
  useApiMutation(
    ({ id, when }: { id: string; when?: string }) => writes.checkInStay(id, when),
    INVALIDATE.stays,
    { success: "Checked in -- rooms are now Occupied" },
  );

export const useCheckOutStay = () =>
  useApiMutation(
    ({ id, when }: { id: string; when?: string }) => writes.checkOutStay(id, when),
    INVALIDATE.stays,
    { success: "Checked out -- rooms released" },
  );

export const useExtendStay = () =>
  useApiMutation(
    ({ id, until }: { id: string; until: string }) => writes.extendStay(id, until),
    INVALIDATE.stays,
    { success: "Check-out extended" },
  );

export const useSetStayStatus = () =>
  useApiMutation(
    ({ id, status }: { id: string; status: writes.StayStatus }) =>
      writes.setStayStatus(id, status),
    INVALIDATE.stays,
    { success: "Booking status updated" },
  );

export const useSetStayDocumentApproval = () =>
  useApiMutation(
    ({ id, approved }: { id: string; approved: boolean }) =>
      writes.setStayDocumentApproval(id, approved),
    INVALIDATE.stays,
    { success: "Document approval updated" },
  );

export const useCancelStay = () =>
  useApiMutation((id: string) => writes.cancelStay(id), INVALIDATE.stays, {
    success: "Booking cancelled -- rooms released",
  });

export const useAllocateRoom = () =>
  useApiMutation(
    ({ stayId, roomId }: { stayId: string; roomId: string }) =>
      writes.allocateRoom(stayId, roomId),
    INVALIDATE.stays,
    { success: "Room allocated" },
  );

export const useReallocateRoom = () =>
  useApiMutation(
    ({ allocationId, roomId }: { allocationId: string; roomId: string }) =>
      writes.reallocateRoom(allocationId, roomId),
    INVALIDATE.stays,
    { success: "Room reallocated" },
  );

export const useReleaseAllocation = () =>
  useApiMutation((allocationId: string) => writes.releaseAllocation(allocationId), INVALIDATE.stays, {
    success: "Room released",
  });

export const useAddOccupant = () =>
  useApiMutation(
    ({ stayId, body }: { stayId: string; body: Parameters<typeof writes.addOccupant>[1] }) =>
      writes.addOccupant(stayId, body),
    INVALIDATE.stays,
    { success: "Occupant added" },
  );

export const useRemoveOccupant = () =>
  useApiMutation((occupantId: string) => writes.removeOccupant(occupantId), INVALIDATE.stays, {
    success: "Occupant removed",
  });

// ---------------------------------------------------------------------------
// Room state
// ---------------------------------------------------------------------------

export const useUpdateRoomState = () =>
  useApiMutation(
    ({ amenityId, body }: { amenityId: string; body: writes.RoomStateWrite }) =>
      writes.updateRoomState(amenityId, body),
    INVALIDATE.occupancy,
    { success: "Room updated" },
  );

export const useSetRoomConditions = () =>
  useApiMutation(
    ({ amenityId, conditionIds }: { amenityId: string; conditionIds: number[] }) =>
      writes.setRoomConditions(amenityId, conditionIds),
    INVALIDATE.occupancy,
    { success: "Room conditions updated" },
  );

// ---------------------------------------------------------------------------
// Devices, firmware, incidents, limit configs
// ---------------------------------------------------------------------------

export const useCreateDevice = (opts?: Options<writes.DeviceWrite, unknown>) =>
  useApiMutation(writes.createDevice, INVALIDATE.devices, { success: "Device added", ...opts });

export const useUpdateDevice = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Parameters<typeof writes.updateDevice>[1] }) =>
      writes.updateDevice(id, body),
    INVALIDATE.devices,
    { success: "Device updated" },
  );

export const useCommissionDevice = () =>
  useApiMutation((id: string) => writes.commissionDevice(id), INVALIDATE.devices, {
    success: "Device commissioned",
  });

export const useDecommissionDevice = () =>
  useApiMutation(
    ({ id, reason }: { id: string; reason?: string | null }) =>
      writes.decommissionDevice(id, reason),
    INVALIDATE.devices,
    { success: "Device decommissioned" },
  );

export const useDeviceMaintenance = () =>
  useApiMutation((id: string) => writes.deviceUnderMaintenance(id), INVALIDATE.devices, {
    success: "Device flagged for maintenance",
  });

export const useCreateFirmware = (opts?: Options<writes.FirmwareWrite, unknown>) =>
  useApiMutation(writes.createFirmware, INVALIDATE.firmware, {
    success: "Firmware added",
    ...opts,
  });

export const useUpdateFirmware = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Partial<writes.FirmwareWrite> }) =>
      writes.updateFirmware(id, body),
    INVALIDATE.firmware,
    { success: "Firmware updated" },
  );

export const useAssignFirmware = () =>
  useApiMutation(
    ({ id, deviceIds }: { id: string; deviceIds: string[] }) =>
      writes.assignFirmware(id, deviceIds),
    INVALIDATE.firmware,
    {
      success: (_data, vars) =>
        `Firmware assigned to ${vars.deviceIds.length} device${
          vars.deviceIds.length === 1 ? "" : "s"
        }`,
    },
  );

export const useUpdateIncident = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: writes.IncidentWrite }) => writes.updateIncident(id, body),
    INVALIDATE.incidents,
    { success: "Incident updated" },
  );

export const useCreateLimitConfig = (opts?: Options<writes.LimitConfigWrite, unknown>) =>
  useApiMutation(writes.createLimitConfig, INVALIDATE.limitConfigs, {
    success: "Limit configuration saved",
    ...opts,
  });

export const useUpdateLimitConfig = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Partial<writes.LimitConfigWrite> }) =>
      writes.updateLimitConfig(id, body),
    INVALIDATE.limitConfigs,
    { success: "Limit configuration updated" },
  );

// ---------------------------------------------------------------------------
// Facility, rooms, catalogue
// ---------------------------------------------------------------------------

export const useUpdateFacility = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: writes.FacilityWrite }) => writes.updateFacility(id, body),
    INVALIDATE.facility,
    { success: "Facility updated" },
  );

export const useCreateRoom = (opts?: Options<writes.RoomWrite, unknown>) =>
  useApiMutation(writes.createRoom, INVALIDATE.catalogue, { success: "Room created", ...opts });

export const useUpdateRoom = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Partial<writes.RoomWrite> }) => writes.updateRoom(id, body),
    INVALIDATE.catalogue,
    { success: "Room updated" },
  );

export const useCreateAmenityType = (opts?: Options<Parameters<typeof writes.createAmenityType>[0], unknown>) =>
  useApiMutation(writes.createAmenityType, INVALIDATE.catalogue, {
    success: "Amenity type created",
    ...opts,
  });

export const useUpdateAmenityType = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Parameters<typeof writes.updateAmenityType>[1] }) =>
      writes.updateAmenityType(id, body),
    INVALIDATE.catalogue,
    { success: "Amenity type updated" },
  );

export const useCreatePackage = (opts?: Options<Parameters<typeof writes.createPackage>[0], unknown>) =>
  useApiMutation(writes.createPackage, INVALIDATE.catalogue, {
    success: "Package created",
    ...opts,
  });

export const useUpdatePackage = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Parameters<typeof writes.updatePackage>[1] }) =>
      writes.updatePackage(id, body),
    INVALIDATE.catalogue,
    { success: "Package updated" },
  );

/**
 * Delete a package. `removePackage` is PATCH status=0 -- the catalogue's soft
 * delete -- and `INVALIDATE.catalogue` refetches /packages, which is what makes
 * the row leave the table instead of the UI pretending it did.
 */
export const useRemovePackage = () =>
  useApiMutation((id: string) => writes.removePackage(id), INVALIDATE.catalogue, {
    success: "Package deleted",
  });

export const useCreateFeature = (opts?: Options<string, unknown>) =>
  useApiMutation(writes.createFeature, INVALIDATE.catalogue, {
    success: "Room amenity created",
    ...opts,
  });

export const useUpdateFeature = () =>
  useApiMutation(
    ({ id, name }: { id: string; name: string }) => writes.updateFeature(id, name),
    INVALIDATE.catalogue,
    { success: "Room amenity updated" },
  );

// ---------------------------------------------------------------------------
// Offers, events, holidays
// ---------------------------------------------------------------------------

export const useCreateOffer = (opts?: Options<writes.OfferWrite, unknown>) =>
  useApiMutation(writes.createOffer, INVALIDATE.offers, { success: "Offer created", ...opts });

export const useUpdateOffer = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Partial<writes.OfferWrite> }) =>
      writes.updateOffer(id, body),
    INVALIDATE.offers,
    { success: "Offer updated" },
  );

export const useCreateEvent = (opts?: Options<writes.EventWrite, unknown>) =>
  useApiMutation(writes.createEvent, INVALIDATE.events, { success: "Event created", ...opts });

export const useUpdateEvent = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Partial<writes.EventWrite> }) =>
      writes.updateEvent(id, body),
    INVALIDATE.events,
    { success: "Event updated" },
  );

export const useCreateHoliday = (opts?: Options<writes.HolidayWrite, unknown>) =>
  useApiMutation(writes.createHoliday, INVALIDATE.holidays, {
    success: "Holiday created",
    ...opts,
  });

export const useUpdateHoliday = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Partial<writes.HolidayWrite> }) =>
      writes.updateHoliday(id, body),
    INVALIDATE.holidays,
    { success: "Holiday updated" },
  );

// ---------------------------------------------------------------------------
// Services Planning
// ---------------------------------------------------------------------------

export const useCreateMaintenanceRequest = (
  opts?: Options<writes.MaintenanceRequestWrite, unknown>,
) =>
  useApiMutation(writes.createMaintenanceRequest, INVALIDATE.maintenance, {
    success: "Planned service created",
    ...opts,
  });

export const useUpdateMaintenanceRequest = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Parameters<typeof writes.updateMaintenanceRequest>[1] }) =>
      writes.updateMaintenanceRequest(id, body),
    INVALIDATE.maintenance,
    { success: "Planned service updated" },
  );

export const useCancelMaintenanceRequest = () =>
  useApiMutation(
    ({ id, reason }: { id: string; reason?: string | null }) =>
      writes.cancelMaintenanceRequest(id, reason),
    INVALIDATE.maintenance,
    { success: "Planned service cancelled" },
  );

/** Soft delete -- `status = 0`. The row and its history survive. */
export const useRemoveMaintenanceRequest = () =>
  useApiMutation(
    ({ id, comments }: { id: string; comments?: string | null }) =>
      writes.removeMaintenanceRequest(id, comments),
    INVALIDATE.maintenance,
    { success: "Planned service removed" },
  );

export const useCreateJobOrder = (opts?: Options<writes.JobOrderWrite, unknown>) =>
  useApiMutation(writes.createJobOrder, INVALIDATE.jobOrders, {
    success: "Job order created",
    ...opts,
  });

export const useUpdateJobOrder = () =>
  useApiMutation(
    ({ id, body }: { id: string; body: Parameters<typeof writes.updateJobOrder>[1] }) =>
      writes.updateJobOrder(id, body),
    INVALIDATE.jobOrders,
    { success: "Job order updated" },
  );

/** Soft delete -- `status = 0`. The room and device links are kept. */
export const useRemoveJobOrder = () =>
  useApiMutation((id: string) => writes.removeJobOrder(id), INVALIDATE.jobOrders, {
    success: "Job order removed",
  });
