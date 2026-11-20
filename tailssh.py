#!/usr/bin/env python3
import getpass
import json
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

TERMINAL_CMD = os.getenv("TERMINAL", "konsole")


# Tailscale Translator:
@dataclass
class Machine:
    ID: str = ""
    NodeID: int = 0
    PublicKey: str = ""
    HostName: str = ""
    DNSName: str = ""
    OS: str = ""
    UserID: int = 0
    TailscaleIPs: list[str] = field(default_factory=list)
    AllowedIPs: list[str] = field(default_factory=list)
    Addrs: list[str] | None = None
    CurAddr: str = ""
    Relay: str = ""
    PeerRelay: str = ""
    RxBytes: int = 0
    TxBytes: int = 0
    Created: str = ""
    LastWrite: str = ""
    LastSeen: str = ""
    LastHandshake: str = ""
    Online: bool = False
    ExitNode: bool = False
    ExitNodeOption: bool = False
    Active: bool = False
    PeerAPIURL: list[str] = field(default_factory=list)
    TaildropTarget: int = 0
    NoFileSharingReason: str = ""
    InNetworkMap: bool = False
    InMagicSock: bool = False
    InEngine: bool = False
    KeyExpiry: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Machine":
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


def getTailStatus() -> dict[str, Any] | None:
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return json.loads(result.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError) as exc:
        print(f">> Failed to read Tailscale status: {exc}")
        return None


def pick_ip(machine: Machine, use_ipv6: bool) -> str:
    ips = machine.TailscaleIPs
    if use_ipv6 and len(ips) > 1:
        return ips[1]
    if ips:
        return ips[0]
    return "?.?.?.?"


def ResolveMachines(Status: dict[str, Any] | None = None) -> dict[str, Machine] | None:
    if Status is None:
        Status = getTailStatus()
    if not Status:
        return None

    peers = Status.get("Peer")
    if not isinstance(peers, dict):
        return None

    return {
        peer_id: Machine.from_dict(peer_data)
        for peer_id, peer_data in peers.items()
        if isinstance(peer_data, dict)
    }


# Console System:
class ConsoleMemory:
    def reload(self) -> None:
        pullstatus = getTailStatus()
        self.Status: dict[str, Any] | None = pullstatus
        self.Machines: dict[str, Machine] | None = ResolveMachines(pullstatus)

    def __init__(self) -> None:
        self.Status: dict[str, Any] | None = None
        self.Machines: dict[str, Machine] | None = None
        self.reload()


def SSH(username: str, IP: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [TERMINAL_CMD, "-e", "ssh", f"{username}@{IP}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def resolve_user(override_user: str | None) -> str:
    if override_user:
        return override_user
    default_user = os.getenv("USER") or getpass.getuser()
    entered = input(f"ssh-user [{default_user}] ~> ").strip()
    return entered or default_user


## Commands
def listmachines(CMemory: ConsoleMemory, args: list[str]) -> None:
    if not CMemory.Machines:
        print(">> Tailscale API may not be available, use 'refresh' to try again.")
        return
    UseIPV6 = "ipv6" in args
    for Machine in CMemory.Machines.values():
        IP = pick_ip(Machine, UseIPV6)
        print(
            IP
            + " - "
            + Machine.HostName
            + (Machine.Online and " (Online)" or " (Offline)")
        )


def listdetails(CMemory: ConsoleMemory, args: list[str]) -> None:
    if not CMemory.Machines:
        print(">> Tailscale API may not be available, use 'refresh' to try again.")
        return
    if not args:
        print(">> Usage: details <hostname>")
        return
    needle = args[0].strip().lower()
    matched = next(
        (
            m
            for m in CMemory.Machines.values()
            if m.HostName.lower() == needle or m.DNSName.split(".")[0].lower() == needle
        ),
        None,
    )
    if not matched:
        print(f">> No machine found matching '{args[0]}'")
        return
    print(f"HostName : {matched.HostName}")
    print(f"DNSName  : {matched.DNSName}")
    print(f"OS       : {matched.OS}")
    print(f"IPs      : {', '.join(matched.TailscaleIPs) or 'none'}")
    print(f"Online   : {matched.Online}")
    print(f"Relay    : {matched.Relay or 'direct/none'}")


def sshmachine(CMemory: ConsoleMemory, args: list[str]) -> None:
    if not CMemory.Machines:
        print(">> Tailscale API may not be available, use 'refresh' to try again.")
        return

    Prechoice: int | None = None
    PreName: str | None = None
    MachineList: list[tuple[str, str, bool]] = [("Close", "exit loop", False)]
    UseIPV6 = "ipv6" in args
    for A in args:
        if A.startswith("index:"):
            _, _, raw_idx = A.partition(":")
            try:
                Prechoice = int(raw_idx)
            except ValueError:
                print(f">> Invalid index '{raw_idx}'")
        elif A.startswith("name:"):
            _, _, raw_name = A.partition(":")
            if raw_name:
                PreName = raw_name

    for Machine in CMemory.Machines.values():
        IP = pick_ip(Machine, UseIPV6)
        MachineList.append((Machine.HostName, IP, Machine.Online))

    if Prechoice is None:
        for index, info in enumerate(MachineList):
            if index != 0:
                print(
                    f" > {index} - {info[0]} ({info[1]}) - {info[2] and 'ONLINE' or 'OFFLINE'}"
                )
            else:
                print(f" > {index} - {info[0]} ({info[1]})")

    while True:
        try:
            if Prechoice is not None:
                Choice = Prechoice
                Prechoice = None
                single_shot = True
            else:
                Choice = int(input("~> ").strip())
                single_shot = False

            if Choice == 0:
                break
            if 0 < Choice < len(MachineList):
                Device = MachineList[Choice]
                User = resolve_user(PreName)
                print(f">>> Trying SSH {Device}")
                SSH(User, Device[1])
            else:
                print(">> Selection out of range.")

            if single_shot:
                break
        except ValueError:
            print(">> Enter a number from the list.")


class ConsoleRuntime:
    def __init__(
        self,
        Commands: dict[str, Callable[[ConsoleMemory, list[str]], str | None]]
        | None = None,
    ) -> None:
        self.Commands: dict[str, Callable[[ConsoleMemory, list[str]], str | None]] = (
            Commands or {}
        )
        self.Memory: ConsoleMemory = ConsoleMemory()

    def MainLoop(self):
        # Prefire commands from args
        ArgLen = len(sys.argv)
        Prechoice: list[str] | None = None
        if ArgLen > 1:
            LaunchArgs = list(sys.argv)
            LaunchArgs.pop(0)
            Prechoice = LaunchArgs
        else:
            print("\n                       < Welcome to Tail-ssh >")
            print("                  >- Run 'help' to get list of commands -<\n")
        while True:
            Choice: list[str] = (
                Prechoice if Prechoice is not None else input("-> ").split(" ")
            )
            if Choice[0] == "exit":
                print(">> Goodbye!")
                break
            Action = self.Commands.get(str(Choice[0] or "?").lower())
            if Action:
                Choice.pop(0)
                Result = Action(self.Memory, Choice)
                if Result:
                    print(f">> {Result}")
            else:
                print(
                    f">> '{Choice[0] or '?'}' Is not an valid command, run 'help' for alist of commands."
                )
            if Prechoice is not None:
                Prechoice = None
                break


if __name__ == "__main__":
    Runtime = ConsoleRuntime()
    PresetCommands: dict[str, Callable[[ConsoleMemory, list[str]], str | None]] = {
        "machines": listmachines,
        "details": listdetails,
        "ssh": sshmachine,
        "refresh": lambda _, __: (Runtime.Memory.reload(), "Reloaded status")[1],
        "exit": lambda _, __: print("<close>"),
    }
    # Help System:
    HelpPrefixs = ["help", "?", "commands", "cmd", "how", "explain"]

    # Helper Command
    def cmd_help(CMemory: ConsoleMemory, args: list[str]) -> str:
        print("Tail-ssh Commands:")
        for CName in PresetCommands:
            if not CName in HelpPrefixs:
                print("- " + CName)
        return " ^ Commands ^"

    # Help Prefix Injector
    for Prefix in HelpPrefixs:
        PresetCommands[Prefix] = cmd_help
    Runtime.Commands = PresetCommands
    Runtime.MainLoop()
