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
import { Info, ArrowRight } from "lucide-react";
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
    if (lowerCondition.includes("maintenance") || lowerCondition.includes("sanitation")) {
      return <Badge key={condition} className="bg-amber-500 text-white text-xs hover:bg-amber-600">{condition}</Badge>;
    }
    if (lowerCondition.includes("low battery")) {
      return <Badge key={condition} className="bg-red-500 text-white text-xs hover:bg-red-600">{condition}</Badge>;
    }
    if (lowerCondition.includes("vip")) {
      return <Badge key={condition} className="bg-purple-500 text-white text-xs hover:bg-purple-600">{condition}</Badge>;
    }
    return <Badge key={condition} className="bg-blue-500 text-white text-xs hover:bg-blue-600">{condition}</Badge>;
  };

  const handleDetailsClick = (room: RoomData) => {
    setSelectedRoom(room);
    setIsModalOpen(true);
  };

  return (
    <div className="space-y-6 animate-fade-in bg-[hsl(220,20%,96%)] min-h-screen -m-6 p-6">
      {/* Header */}
      <div className="mb-2">
        <h1 className="text-2xl font-semibold text-foreground">Occupancy Management</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-muted/30 p-1 rounded-xl w-fit">
        <button
          onClick={() => setActiveTab("guest")}
          className={`px-6 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 ${activeTab === "guest"
            ? "bg-white text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground"
            }`}
        >
          Guest
        </button>
        <button
          onClick={() => setActiveTab("nonGuest")}
          className={`px-6 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 ${activeTab === "nonGuest"
            ? "bg-white text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground"
            }`}
        >
          Non Guest
        </button>
      </div>

      {/* Table Container */}
      <Card className="border-0 shadow-lg rounded-2xl bg-white">
        <CardContent className="p-6">
          {/* Controls */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground text-sm">Show</span>
              <Select value={entriesPerPage} onValueChange={setEntriesPerPage}>
                <SelectTrigger className="w-20 h-9 bg-muted/30 border-border/50">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-white">
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
                  <SelectTrigger className="w-28 h-9 bg-muted/30 border-border/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
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
                  className="w-64 h-9 bg-muted/30 border-border/50"
                />
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="rounded-xl overflow-hidden border border-gray-200">
            <Table>
              <TableHeader>
                <TableRow className="bg-gray-50 hover:bg-gray-50 border-b border-gray-200">
                  <TableHead className="text-gray-600 font-medium">Room No</TableHead>
                  <TableHead className="text-gray-600 font-medium">Room Type</TableHead>
                  <TableHead className="text-gray-600 font-medium">Guest name</TableHead>
                  <TableHead className="text-gray-600 font-medium text-center">Generate <span className="text-gray-400">↓</span></TableHead>
                  <TableHead className="text-gray-600 font-medium text-center">Status</TableHead>
                  <TableHead className="text-gray-600 font-medium text-center">Condition</TableHead>
                  <TableHead className="text-gray-600 font-medium text-center">Details</TableHead>
                  <TableHead className="text-gray-600 font-medium text-center">Reallocate</TableHead>
                  <TableHead className="text-gray-600 font-medium text-center">Invoice <span className="text-gray-400">↓</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRooms.map((room, index) => (
                  <TableRow
                    key={room.roomNo}
                    className={`${index % 2 === 0 ? "bg-muted/20" : "bg-white"} hover:bg-muted/40`}
                  >
                    <TableCell>{room.roomNo}</TableCell>
                    <TableCell>{room.roomType}</TableCell>
                    <TableCell>{room.guestName}</TableCell>
                    <TableCell className="text-center">
                      <Button size="sm" className="bg-teal-600 hover:bg-teal-700 text-white text-xs px-3">
                        Generate
                      </Button>
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge
                        variant="outline"
                        className={`${room.status === "Available"
                          ? "border-green-500 text-green-600"
                          : "border-gray-400 text-gray-500"
                          }`}
                      >
                        {room.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex flex-wrap gap-1 justify-center">
                        {room.conditions.length > 0
                          ? room.conditions.map((condition) => getConditionBadge(condition))
                          : <span className="text-gray-400">-</span>}
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
                      <Button size="sm" variant="outline" className="border-cyan-500 text-cyan-600 hover:bg-cyan-50 w-8 h-8 p-0">
                        <Info className="h-4 w-4" />
                      </Button>
                    </TableCell>
                    <TableCell className="text-center">
                      <Button size="sm" className="bg-cyan-600 hover:bg-cyan-700 text-white w-8 h-8 p-0">
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </TableCell>
                    <TableCell className="text-center">
                      <Button size="sm" variant="outline" className="border-cyan-500 text-cyan-600 hover:bg-cyan-50 text-xs px-3">
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


