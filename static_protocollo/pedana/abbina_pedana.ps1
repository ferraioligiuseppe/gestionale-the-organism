# ─────────────────────────────────────────────────────────────────────
#  Abbina la pedana Wii (Balance Board) a Windows — Studio The Organism
#  Fa quello che fa Dolphin: trova la pedana e usa il PIN giusto
#  (l'indirizzo Bluetooth del computer), poi attiva il servizio HID.
#  Non installa nulla e non modifica altro.
# ─────────────────────────────────────────────────────────────────────
$ErrorActionPreference = "Stop"
$codice = @"
using System;
using System.Runtime.InteropServices;
public static class Bt {
  [StructLayout(LayoutKind.Sequential)] public struct FIND_RADIO_PARAMS { public uint dwSize; }
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] public struct RADIO_INFO {
    public uint dwSize; public ulong address;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 248)] public string szName;
    public uint ulClassofDevice; public ushort lmpSubversion; public ushort manufacturer; }
  [StructLayout(LayoutKind.Sequential)] public struct SYSTEMTIME { public ushort a,b,c,d,e,f,g,h; }
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] public struct DEVICE_INFO {
    public uint dwSize; public ulong Address; public uint ulClassofDevice;
    public int fConnected; public int fRemembered; public int fAuthenticated;
    public SYSTEMTIME stLastSeen; public SYSTEMTIME stLastUsed;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 248)] public string szName; }
  [StructLayout(LayoutKind.Sequential)] public struct SEARCH_PARAMS {
    public uint dwSize; public int fReturnAuthenticated; public int fReturnRemembered;
    public int fReturnUnknown; public int fReturnConnected; public int fIssueInquiry;
    public byte cTimeoutMultiplier; public IntPtr hRadio; }

  [DllImport("BluetoothApis.dll", SetLastError = true)] public static extern IntPtr BluetoothFindFirstRadio(ref FIND_RADIO_PARAMS p, out IntPtr hRadio);
  [DllImport("BluetoothApis.dll", SetLastError = true)] public static extern bool BluetoothFindRadioClose(IntPtr hFind);
  [DllImport("BluetoothApis.dll", SetLastError = true)] public static extern uint BluetoothGetRadioInfo(IntPtr hRadio, ref RADIO_INFO info);
  [DllImport("BluetoothApis.dll", SetLastError = true)] public static extern IntPtr BluetoothFindFirstDevice(ref SEARCH_PARAMS p, ref DEVICE_INFO info);
  [DllImport("BluetoothApis.dll", SetLastError = true)] public static extern bool BluetoothFindNextDevice(IntPtr hFind, ref DEVICE_INFO info);
  [DllImport("BluetoothApis.dll", SetLastError = true)] public static extern bool BluetoothFindDeviceClose(IntPtr hFind);
  [DllImport("BluetoothApis.dll", SetLastError = true)] public static extern uint BluetoothRemoveDevice(ref ulong address);
  [DllImport("BluetoothApis.dll", SetLastError = true, CharSet = CharSet.Unicode)]
  public static extern uint BluetoothAuthenticateDevice(IntPtr hwnd, IntPtr hRadio, ref DEVICE_INFO info,
      [MarshalAs(UnmanagedType.LPArray)] char[] passkey, uint len);
  [DllImport("BluetoothApis.dll", SetLastError = true)]
  public static extern uint BluetoothSetServiceState(IntPtr hRadio, ref DEVICE_INFO info, ref Guid service, uint flags);
  [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);

  public static IntPtr Radio(out RADIO_INFO info) {
    var p = new FIND_RADIO_PARAMS(); p.dwSize = (uint)Marshal.SizeOf(typeof(FIND_RADIO_PARAMS));
    IntPtr hRadio; IntPtr f = BluetoothFindFirstRadio(ref p, out hRadio);
    info = new RADIO_INFO(); info.dwSize = (uint)Marshal.SizeOf(typeof(RADIO_INFO));
    if (f == IntPtr.Zero) return IntPtr.Zero;
    BluetoothFindRadioClose(f);
    BluetoothGetRadioInfo(hRadio, ref info);
    return hRadio;
  }

  // Cerca e abbina. Ritorna un messaggio leggibile.
  public static string Abbina(IntPtr hRadio, RADIO_INFO radio) {
    var sp = new SEARCH_PARAMS();
    sp.dwSize = (uint)Marshal.SizeOf(typeof(SEARCH_PARAMS));
    sp.fReturnAuthenticated = 1; sp.fReturnRemembered = 1; sp.fReturnUnknown = 1;
    sp.fReturnConnected = 1; sp.fIssueInquiry = 1; sp.cTimeoutMultiplier = 4; sp.hRadio = hRadio;
    var di = new DEVICE_INFO(); di.dwSize = (uint)Marshal.SizeOf(typeof(DEVICE_INFO));
    IntPtr f = BluetoothFindFirstDevice(ref sp, ref di);
    if (f == IntPtr.Zero) return "";
    string esito = "";
    do {
      string nome = di.szName ?? "";
      if (nome.Contains("RVL-WBC") || nome.Contains("RVL-CNT")) {
        if (di.fConnected != 0 && di.fAuthenticated != 0) { esito = "GIA|" + nome; break; }
        if (di.fRemembered != 0) { ulong a = di.Address; BluetoothRemoveDevice(ref a); }   // abbinamento vecchio o sbagliato
        // PIN = indirizzo Bluetooth del computer (6 byte), come per il tasto rosso di sincronizzazione
        byte[] b = BitConverter.GetBytes(radio.address);
        char[] pin = new char[6]; for (int i = 0; i < 6; i++) pin[i] = (char)b[i];
        uint r = BluetoothAuthenticateDevice(IntPtr.Zero, hRadio, ref di, pin, 6);
        Guid hid = new Guid("00001124-0000-1000-8000-00805F9B34FB");
        uint s = BluetoothSetServiceState(hRadio, ref di, ref hid, 1);
        esito = (r == 0 ? "OK|" : "ERR" + r + "|") + nome + "|" + s;
        break;
      }
      di.dwSize = (uint)Marshal.SizeOf(typeof(DEVICE_INFO));
    } while (BluetoothFindNextDevice(f, ref di));
    BluetoothFindDeviceClose(f);
    return esito;
  }
}
"@
Add-Type -TypeDefinition $codice

Write-Host ""
Write-Host "  ABBINAMENTO PEDANA WII — Studio The Organism" -ForegroundColor Green
Write-Host "  ─────────────────────────────────────────────"
$radio = New-Object Bt+RADIO_INFO
$h = [Bt]::Radio([ref]$radio)
if ($h -eq [IntPtr]::Zero) {
  Write-Host "  Nessun Bluetooth trovato su questo computer. Accendilo (Impostazioni > Bluetooth) e riprova." -ForegroundColor Red
  Read-Host "  Premi Invio per chiudere"; exit 1
}
Write-Host "  Bluetooth del computer: $($radio.szName)"
Write-Host ""
Write-Host "  1. Metti le pile nella pedana."
Write-Host "  2. Apri lo sportellino delle pile e premi il TASTINO ROSSO: la luce blu lampeggia."
Read-Host "  3. Appena lampeggia, premi Invio qui"

for ($tentativo = 1; $tentativo -le 6; $tentativo++) {
  Write-Host "  Cerco la pedana... (tentativo $tentativo di 6)"
  $esito = [Bt]::Abbina($h, $radio)
  if ($esito -like "GIA|*") {
    Write-Host "  La pedana è già abbinata e collegata. Puoi usarla." -ForegroundColor Green; break }
  if ($esito -like "OK|*") {
    Write-Host ""
    Write-Host "  FATTO! Pedana abbinata ($($esito.Split('|')[1]))." -ForegroundColor Green
    Write-Host "  La luce blu deve restare fissa. Ora apri la pagina della pedana in Chrome e premi «Collega la pedana»."
    break }
  if ($esito -like "ERR*") {
    Write-Host "  La pedana ha risposto ma l'abbinamento non è riuscito (codice $($esito.Split('|')[0])). Ripremi il tastino rosso." -ForegroundColor Yellow
    Read-Host "  Quando la luce lampeggia, premi Invio"; continue }
  Write-Host "  Non la vedo ancora. Se la luce ha smesso di lampeggiare, ripremi il tastino rosso." -ForegroundColor Yellow
}
if (-not ($esito -like "OK|*" -or $esito -like "GIA|*")) {
  Write-Host ""
  Write-Host "  Non sono riuscito ad abbinarla. Controlla le pile e che il Bluetooth sia acceso, poi riprova." -ForegroundColor Red
  Write-Host "  In alternativa usa Dolphin (Controller > Balance Board reale > Scansione continua)."
}
[Bt]::CloseHandle($h) | Out-Null
Read-Host "  Premi Invio per chiudere"
