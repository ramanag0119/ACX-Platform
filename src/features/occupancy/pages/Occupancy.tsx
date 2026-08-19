import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Info, ArrowRight, Wrench, ShieldCheck, BatteryLow, Star, UserCheck, Clock, Minus } from "lucide-react";
import { RoomDetailsModal } from "../components/RoomDetailsModal";

type RoomData = {
  roomNo: string;
  roomType: string;
  guestName: string;
  status: "Available" | "Unavailable";
  conditions: string[];
};

const guestRooms: RoomData[] = [
  { roomNo: "201", roomType: "Deluxe Suite", guestName: "John Smith", status: "Unavailable", conditions: ["Occupied"] },
  { roomNo: "202", roomType: "Standard Room", guestName: "Jane Doe", status: "Unavailable", conditions: ["Occupied"] },
  { roomNo: "203", roomType: "Premium Suite", guestName: "Bob Johnson", status: "Unavailable", conditions: ["Occupied", "VIP"] },
  { roomNo: "204", roomType: "Deluxe Suite", guestName: "Alice Brown", status: "Unavailable", conditions: ["Occupied"] },
  { roomNo: "205", roomType: "Standard Room", guestName: "Charlie Wilson", status: "Unavailable", conditions: ["Occupied"] },
  { roomNo: "206", roomType: "Executive Suite", guestName: "Diana Prince", status: "Unavailable", conditions: ["Occupied", "Late checkout"] },
  { roomNo: "301", roomType: "Penthouse", guestName: "Bruce Wayne", status: "Unavailable", conditions: ["Occupied", "VIP"] },
  { roomNo: "302", roomType: "Deluxe Suite", guestName: "Clark Kent", status: "Unavailable", conditions: ["Occupied"] },
  { roomNo: "303", roomType: "Standard Room", guestName: "Peter Parker", status: "Unavailable", conditions: ["Occupied"] },
  { roomNo: "304", roomType: "Premium Suite", guestName: "Tony Stark", status: "Unavailable", conditions: ["Occupied", "VIP"] },
];

const nonGuestRooms: RoomData[] = [
  { roomNo: "101", roomType: "Stack Room", guestName: "-", status: "Unavailable", conditions: ["Under maintenance"] },
  { roomNo: "102", roomType: "South Indian Restaurant", guestName: "-", status: "Unavailable", conditions: ["Under maintenance"] },
  { roomNo: "103", roomType: "Store", guestName: "-", status: "Available", conditions: [] },
  { roomNo: "104", roomType: "South Indian Restaurant", guestName: "-", status: "Unavailable", conditions: ["Sanitation"] },
  { roomNo: "105", roomType: "South Indian Restaurant", guestName: "-", status: "Unavailable", conditions: ["Under maintenance"] },
  { roomNo: "109", roomType: "food", guestName: "-", status: "Unavailable", conditions: ["Under maintenance"] },
  { roomNo: "1309", roomType: "South Indian Restaurant", guestName: "-", status: "Unavailable", conditions: ["Under maintenance"] },
  { roomNo: "241", roomType: "South Indian Restaurant", guestName: "-", status: "Unavailable", conditions: ["Under maintenance"] },
  { roomNo: "3", roomType: "South Indian Restaurant", guestName: "-", status: "Unavailable", conditions: ["Under maintenance"] },
  { roomNo: "3002", roomType: "food", guestName: "-", status: "Unavailable", conditions: ["Low Battery", "Under maintenance"] },
];



const Occupancy = () => {
  const [activeTab, setActiveTab] = useState<"guest" | "nonGuest">("guest");
  const [entriesPerPage, setEntriesPerPage] = useState("10");
  const [searchQuery, setSearchQuery] = useState("");
  const [filterBy, setFilterBy] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedRoom, setSelectedRoom] = useState<RoomData | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const rooms = activeTab === "guest" ? guestRooms : nonGuestRooms;

  const filteredRooms = rooms.filter((room) => {
    const matchesSearch =
      room.roomNo.toLowerCase().includes(searchQuery.toLowerCase()) ||
      room.roomType.toLowerCase().includes(searchQuery.toLowerCase()) ||
      room.guestName.toLowerCase().includes(searchQuery.toLowerCase());

    if (filterBy === "all") return matchesSearch;
    if (filterBy === "available") return matchesSearch && room.status === "Available";
    if (filterBy === "unavailable") return matchesSearch && room.status === "Unavailable";
    return matchesSearch;
  });

  const totalEntries = filteredRooms.length;
  const pageSize = parseInt(entriesPerPage) || 10;
  const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalEntries);
  const paginatedRooms = filteredRooms.slice(startIndex, endIndex);

  const getConditionBadge = (condition: string) => {
    const lowerCondition = condition.toLowerCase();
    if (lowerCondition.includes("maintenance")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-500/40 dark:bg-orange-950/60 dark:text-orange-400 text-[11.5px] font-medium">
          <Wrench className="h-3 w-3 text-orange-600 dark:text-orange-400" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("sanitation")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/40 dark:bg-emerald-950/60 dark:text-emerald-400 text-[11.5px] font-medium">
          <ShieldCheck className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("low battery")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/40 dark:bg-rose-950/60 dark:text-rose-400 text-[11.5px] font-medium">
          <BatteryLow className="h-3 w-3 text-rose-600 dark:text-rose-400" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("vip")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-500/40 dark:bg-purple-950/60 dark:text-purple-300 text-[11.5px] font-medium">
          <Star className="h-3 w-3 text-purple-600 dark:text-purple-300" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("occupied")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/40 dark:bg-amber-950/60 dark:text-amber-300 text-[11.5px] font-medium">
          <UserCheck className="h-3 w-3 text-amber-600 dark:text-amber-300" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("late checkout")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/40 dark:bg-amber-950/60 dark:text-amber-400 text-[11.5px] font-medium">
          <Clock className="h-3 w-3 text-amber-600 dark:text-amber-400" />
          {condition}
        </span>
      );
    }
    return (
      <span key={condition} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700/60 dark:bg-slate-800/60 dark:text-slate-400 text-[11.5px] font-medium">
        <Minus className="h-3 w-3" />
        {condition}
      </span>
    );
  };

  const handleDetailsClick = (room: RoomData) => {
    setSelectedRoom(room);
    setIsModalOpen(true);
  };

  return (
    <div className="space-y-5 animate-fade-in text-foreground">
      {/* Header */}
      <div className="mb-2">
        <h1 className="text-xl font-semibold text-foreground tracking-tight">Occupancy Management</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-6 border-b border-border dark:border-slate-800">
        <button
          onClick={() => setActiveTab("guest")}
          className={`relative px-1 pb-2.5 text-xs font-semibold uppercase tracking-wider transition-all duration-200 ${activeTab === "guest"
            ? "text-foreground font-semibold"
            : "text-muted-foreground hover:text-foreground"
            }`}
        >
          Guest
          {activeTab === "guest" && (
            <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-primary rounded-t-full" />
          )}
        </button>
        <button
          onClick={() => setActiveTab("nonGuest")}
          className={`relative px-1 pb-2.5 text-xs font-semibold uppercase tracking-wider transition-all duration-200 ${activeTab === "nonGuest"
            ? "text-foreground font-semibold"
            : "text-muted-foreground hover:text-foreground"
            }`}
        >
          Non Guest
          {activeTab === "nonGuest" && (
            <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-primary rounded-t-full" />
          )}
        </button>
      </div>

      {/* Table Container */}
      <Card className="border border-border/80 dark:border-slate-800 shadow-xl rounded-xl bg-card text-card-foreground overflow-hidden">
        <CardContent className="p-5">
          {/* Controls */}
          <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground text-xs font-medium">Show</span>
              <Select value={entriesPerPage} onValueChange={setEntriesPerPage}>
                <SelectTrigger className="w-18 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-popover text-popover-foreground border-border text-xs">
                  <SelectItem value="10">10</SelectItem>
                  <SelectItem value="25">25</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                </SelectContent>
              </Select>
              <span className="text-muted-foreground text-xs font-medium">entries</span>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground text-xs font-medium">Filter By</span>
                <Select value={filterBy} onValueChange={setFilterBy}>
                  <SelectTrigger className="w-28 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground border-border text-xs">
                    <SelectItem value="all">Show All</SelectItem>
                    <SelectItem value="available">Available</SelectItem>
                    <SelectItem value="unavailable">Unavailable</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-muted-foreground text-xs font-medium">Search:</span>
                <Input
                  placeholder="Room no, Room type, Guest name"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-56 md:w-64 h-8 text-xs bg-muted/20 border-border dark:border-slate-700/80 rounded-md placeholder:text-muted-foreground/60"
                />
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="rounded-lg overflow-hidden border border-border/80 dark:border-slate-800">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 dark:bg-[#0e1322] hover:bg-muted/40 dark:hover:bg-[#0e1322] border-b border-border dark:border-slate-800">
                  <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-3 px-4">Room No</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-3 px-4">Room Type</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-3 px-4">Guest name</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-3 px-4 text-center">Generate</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-3 px-4 text-center">Status</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-3 px-4 text-center">Condition</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-3 px-4 text-center">Details</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-3 px-4 text-center">Reallocate</TableHead>
                  <TableHead className="text-muted-foreground dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider py-3 px-4 text-center">Invoice</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedRooms.length > 0 ? (
                  paginatedRooms.map((room, index) => (
                    <TableRow
                      key={room.roomNo}
                      className={`${index % 2 === 0 ? "bg-card dark:bg-[#101526]/80" : "bg-muted/10 dark:bg-[#0d1120]/80"} hover:bg-muted/30 dark:hover:bg-slate-800/50 border-b border-border/50 dark:border-slate-800/70 transition-colors`}
                    >
                      <TableCell className="font-medium text-[13px] text-foreground py-3 px-4">{room.roomNo}</TableCell>
                      <TableCell className="text-[13px] text-foreground/90 py-3 px-4">{room.roomType}</TableCell>
                      <TableCell className="text-[13px] text-foreground/90 py-3 px-4">{room.guestName}</TableCell>
                      
                      {/* Action Button: Generate */}
                      <TableCell className="text-center py-3 px-4">
                        <button className="inline-flex items-center justify-center h-8 px-3 rounded-lg text-xs font-medium text-white bg-teal-600 hover:bg-teal-700 dark:bg-teal-600 dark:hover:bg-teal-500 shadow-sm transition-all hover:scale-105 active:scale-95">
                          Generate
                        </button>
                      </TableCell>

                      {/* Status Pill Badge: Green for Available, Red for Unavailable */}
                      <TableCell className="text-center py-3 px-4">
                        <span
                          className={`inline-flex items-center justify-center px-3 py-0.5 rounded-full text-[11.5px] font-medium border ${room.status === "Available"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:border-emerald-500/40 dark:bg-emerald-950/60 dark:text-emerald-400"
                            : "bg-rose-50 text-rose-700 border-rose-200 dark:border-rose-500/40 dark:bg-rose-950/60 dark:text-rose-400"
                            }`}
                        >
                          {room.status}
                        </span>
                      </TableCell>

                      {/* Condition Pill Badge */}
                      <TableCell className="text-center py-3 px-4">
                        <div className="flex flex-wrap gap-1.5 justify-center">
                          {room.conditions.length > 0
                            ? room.conditions.map((condition) => getConditionBadge(condition))
                            : <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border border-slate-200 bg-slate-100 text-slate-500 dark:border-slate-700/60 dark:bg-slate-800/60 dark:text-slate-400 text-[11.5px] font-medium">
                                <Minus className="h-3 w-3" /> -
                              </span>}
                        </div>
                      </TableCell>

                      {/* Action Button: Details */}
                      <TableCell className="text-center py-3 px-4">
                        <button
                          className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-amber-500 hover:bg-amber-600 text-white shadow-sm transition-all hover:scale-105 active:scale-95"
                          onClick={() => handleDetailsClick(room)}
                          title="View Details"
                        >
                          <Info className="h-4 w-4 stroke-[2.2]" />
                        </button>
                      </TableCell>

                      {/* Action Button: Reallocate */}
                      <TableCell className="text-center py-3 px-4">
                        <button 
                          className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-cyan-600 hover:bg-cyan-700 text-white shadow-sm transition-all hover:scale-105 active:scale-95"
                          title="Reallocate"
                        >
                          <ArrowRight className="h-4 w-4 stroke-[2.2]" />
                        </button>
                      </TableCell>

                      {/* Action Button: Invoice */}
                      <TableCell className="text-center py-3 px-4">
                        <button className="inline-flex items-center justify-center h-8 px-3 rounded-lg text-xs font-medium text-cyan-700 bg-cyan-50 hover:bg-cyan-600 hover:text-white border border-cyan-300 dark:text-cyan-300 dark:bg-cyan-950/60 dark:border-cyan-500/40 dark:hover:bg-cyan-600 dark:hover:text-white shadow-sm transition-all">
                          Invoice
                        </button>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-6 text-muted-foreground text-xs">
                      No rooms found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="flex flex-wrap items-center justify-between gap-4 mt-5">
            <span className="text-muted-foreground text-xs">
              Showing {totalEntries > 0 ? startIndex + 1 : 0} to {endIndex} of {totalEntries} entries
            </span>

            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
              <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                <Button
                  key={page}
                  variant={currentPage === page ? "default" : "ghost"}
                  size="sm"
                  className={`h-8 w-8 p-0 text-xs rounded-xl ${currentPage === page ? "bg-[#5865F2] hover:bg-[#4752c4] text-white font-semibold shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
                  onClick={() => setCurrentPage(page)}
                >
                  {page}
                </Button>
              ))}
              <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>Next</Button>
              <Button variant="ghost" size="sm" className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>Last</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <RoomDetailsModal
        roomNo={selectedRoom?.roomNo ?? null}
        roomType={selectedRoom?.roomType}
        guestName={selectedRoom?.guestName}
        status={selectedRoom?.status}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
};

export default Occupancy;


