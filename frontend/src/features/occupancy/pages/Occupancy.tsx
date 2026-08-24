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
  const totalEntries = 40;
  const totalPages = Math.ceil(totalEntries / parseInt(entriesPerPage));

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

  const getConditionBadge = (condition: string) => {
    const lowerCondition = condition.toLowerCase();
    if (lowerCondition.includes("maintenance")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-orange-200 bg-orange-50 text-orange-700 dark:border-amber-800/60 dark:bg-amber-950/70 dark:text-amber-300 text-xs font-semibold uppercase tracking-wide">
          <Wrench className="h-3.5 w-3.5 text-orange-600 dark:text-amber-300" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("sanitation")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-green-200 bg-green-50 text-green-700 dark:border-emerald-800/60 dark:bg-emerald-950/70 dark:text-emerald-300 text-xs font-semibold uppercase tracking-wide">
          <ShieldCheck className="h-3.5 w-3.5 text-green-600 dark:text-emerald-300" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("low battery")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-red-200 bg-red-50 text-red-700 dark:border-rose-800/60 dark:bg-rose-950/70 dark:text-rose-300 text-xs font-semibold uppercase tracking-wide">
          <BatteryLow className="h-3.5 w-3.5 text-red-600 dark:text-rose-300" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("vip")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-800/60 dark:bg-purple-950/70 dark:text-purple-300 text-xs font-semibold uppercase tracking-wide">
          <Star className="h-3.5 w-3.5 text-purple-600 dark:text-purple-300" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("occupied")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800/60 dark:bg-blue-950/70 dark:text-blue-300 text-xs font-semibold uppercase tracking-wide">
          <UserCheck className="h-3.5 w-3.5 text-blue-600 dark:text-blue-300" />
          {condition}
        </span>
      );
    }
    if (lowerCondition.includes("late checkout")) {
      return (
        <span key={condition} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800/60 dark:bg-amber-950/70 dark:text-amber-300 text-xs font-semibold uppercase tracking-wide">
          <Clock className="h-3.5 w-3.5 text-amber-600 dark:text-amber-300" />
          {condition}
        </span>
      );
    }
    return (
      <span key={condition} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-gray-200 bg-gray-50 text-gray-500 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-400 text-xs font-semibold uppercase tracking-wide">
        <Minus className="h-3.5 w-3.5" />
        {condition}
      </span>
    );
  };

  const handleDetailsClick = (room: RoomData) => {
    setSelectedRoom(room);
    setIsModalOpen(true);
  };

  return (
    <div className="space-y-6 animate-fade-in bg-background min-h-screen -m-6 p-6 text-foreground">
      {/* Header */}
      <div className="mb-2">
        <h1 className="text-2xl font-semibold text-foreground">Occupancy Management</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-6 border-b border-gray-200 dark:border-slate-800">
        <button
          onClick={() => setActiveTab("guest")}
          className={`relative px-1 pb-3 text-sm font-medium transition-all duration-200 ${activeTab === "guest"
            ? "text-foreground font-semibold"
            : "text-muted-foreground hover:text-foreground"
            }`}
        >
          Guest
          {activeTab === "guest" && (
            <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-purple-600 rounded-t-full" />
          )}
        </button>
        <button
          onClick={() => setActiveTab("nonGuest")}
          className={`relative px-1 pb-3 text-sm font-medium transition-all duration-200 ${activeTab === "nonGuest"
            ? "text-foreground font-semibold"
            : "text-muted-foreground hover:text-foreground"
            }`}
        >
          Non Guest
          {activeTab === "nonGuest" && (
            <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-purple-600 rounded-t-full" />
          )}
        </button>
      </div>

      {/* Table Container */}
      <Card className="border border-border/60 dark:border-slate-800/80 shadow-lg rounded-2xl bg-card text-card-foreground">
        <CardContent className="p-6">
          {/* Controls */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground text-sm">Show</span>
              <Select value={entriesPerPage} onValueChange={setEntriesPerPage}>
                <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50 dark:border-slate-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-popover text-popover-foreground border-border">
                  <SelectItem value="10">10</SelectItem>
                  <SelectItem value="25">25</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                </SelectContent>
              </Select>
              <span className="text-muted-foreground text-sm">entries</span>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground text-sm">Filter By</span>
                <Select value={filterBy} onValueChange={setFilterBy}>
                  <SelectTrigger className="w-28 h-9 bg-muted/30 border-border/50 dark:border-slate-700">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground border-border">
                    <SelectItem value="all">Show All</SelectItem>
                    <SelectItem value="available">Available</SelectItem>
                    <SelectItem value="unavailable">Unavailable</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-muted-foreground text-sm">Search:</span>
                <Input
                  placeholder="Room no, Room type, Guest name"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-64 h-9 bg-muted/30 border-border/50 dark:border-slate-700"
                />
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="rounded-xl overflow-hidden border border-gray-200 dark:border-slate-800">
            <Table>
              <TableHeader>
                <TableRow className="bg-gray-50/80 dark:bg-slate-800/60 hover:bg-gray-50 dark:hover:bg-slate-800/60 border-b border-gray-200 dark:border-slate-800">
                  <TableHead className="text-gray-600 dark:text-slate-300 font-medium">Room No</TableHead>
                  <TableHead className="text-gray-600 dark:text-slate-300 font-medium">Room Type</TableHead>
                  <TableHead className="text-gray-600 dark:text-slate-300 font-medium">Guest name</TableHead>
                  <TableHead className="text-gray-600 dark:text-slate-300 font-medium text-center">Generate <span className="text-gray-400 dark:text-slate-500">↓</span></TableHead>
                  <TableHead className="text-gray-600 dark:text-slate-300 font-medium text-center">Status</TableHead>
                  <TableHead className="text-gray-600 dark:text-slate-300 font-medium text-center">Condition</TableHead>
                  <TableHead className="text-gray-600 dark:text-slate-300 font-medium text-center">Details</TableHead>
                  <TableHead className="text-gray-600 dark:text-slate-300 font-medium text-center">Reallocate</TableHead>
                  <TableHead className="text-gray-600 dark:text-slate-300 font-medium text-center">Invoice <span className="text-gray-400 dark:text-slate-500">↓</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRooms.map((room, index) => (
                  <TableRow
                    key={room.roomNo}
                    className={`${index % 2 === 0 ? "bg-card dark:bg-slate-900/60" : "bg-muted/20 dark:bg-slate-800/40"} hover:bg-muted/40 dark:hover:bg-slate-800/80 border-b border-border/40 dark:border-slate-800/50`}
                  >
                    <TableCell className="font-medium text-foreground">{room.roomNo}</TableCell>
                    <TableCell className="text-foreground">{room.roomType}</TableCell>
                    <TableCell className="text-foreground">{room.guestName}</TableCell>
                    <TableCell className="text-center">
                      <Button size="sm" className="bg-teal-600 hover:bg-purple-600 text-white text-xs px-3">
                        Generate
                      </Button>
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge
                        variant="outline"
                        className={`${room.status === "Available"
                          ? "border-green-500 text-green-600 dark:text-green-400 dark:border-green-500/60 dark:bg-green-950/30"
                          : "border-gray-400 text-gray-500 dark:text-gray-400 dark:border-gray-600 dark:bg-slate-800/40"
                          }`}
                      >
                        {room.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex flex-wrap gap-1 justify-center">
                        {room.conditions.length > 0
                          ? room.conditions.map((condition) => getConditionBadge(condition))
                          : <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-gray-200 bg-gray-50 text-gray-400 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-400 text-xs font-semibold">
                              <Minus className="h-3.5 w-3.5" /> -
                            </span>}
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      <Button
                        size="sm"
                        className="bg-amber-500 hover:bg-amber-600 text-white w-8 h-8 p-0"
                        onClick={() => handleDetailsClick(room)}
                      >
                        <Info className="h-4 w-4" />
                      </Button>
                    </TableCell>
                    <TableCell className="text-center">
                      <Button size="sm" className="bg-cyan-600 hover:bg-cyan-700 text-white w-8 h-8 p-0">
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </TableCell>
                    <TableCell className="text-center">
                      <Button size="sm" variant="outline" className="border-cyan-500 text-cyan-600 hover:bg-cyan-50 dark:text-cyan-400 dark:hover:bg-cyan-950/50 text-xs px-3">
                        Invoice
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-6">
            <span className="text-muted-foreground text-sm">
              Showing 1 to {Math.min(parseInt(entriesPerPage), filteredRooms.length)} of {totalEntries} entries
            </span>

            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>First</Button>
              <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>Previous</Button>
              {[1, 2, 3, 4].map((page) => (
                <Button
                  key={page}
                  variant={currentPage === page ? "default" : "ghost"}
                  size="sm"
                  className={`w-9 h-9 p-0 ${currentPage === page ? "bg-cyan-600 text-white" : "text-muted-foreground"}`}
                  onClick={() => setCurrentPage(page)}
                >
                  {page}
                </Button>
              ))}
              <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>Next</Button>
              <Button variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}>Last</Button>
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


