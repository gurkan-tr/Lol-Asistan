"""Konsol arayüzü (rich kütüphanesi)."""
from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .champs import ROLLER, ROL_AD, SINIF_AD

konsol = Console()


def _hasar_renk(h):
    return {"AD": "orange3", "AP": "medium_purple1", "MIX": "cyan"}.get(h, "white")


def bekle(mesaj):
    konsol.clear()
    konsol.print(Panel(Text.from_markup(mesaj, justify="center"), title="[bold gold1]LoL Asistan",
                       border_style="gold1", padding=(1, 4)))


def goster(rol, benim, rakip_roller, profil, oneriler, build, durum="", benim_kilitli=False):
    konsol.clear()
    baslik = f"[bold gold1]LoL Asistan[/]  ·  Koridorun: [bold]{ROL_AD.get(rol, '?')}[/]"
    if durum:
        baslik += f"  ·  [dim]{durum}[/]"
    konsol.rule(baslik, style="gold1")

    # Rakip takım
    t = Table(box=box.SIMPLE_HEAD, expand=True, title="Rakip takım (tahmini koridorlar)",
              title_style="bold red", header_style="bold")
    t.add_column("Koridor")
    t.add_column("Şampiyon")
    t.add_column("Sınıf")
    t.add_column("Hasar")
    for r in ROLLER:
        s = rakip_roller.get(r)
        isaret = " ◄ senin rakibin" if r == rol and s else ""
        if s:
            t.add_row(ROL_AD[r], f"[bold]{s.ad}[/][yellow]{isaret}[/]", SINIF_AD.get(s.sinif, s.sinif),
                      f"[{_hasar_renk(s.hasar)}]{s.hasar}[/]")
        else:
            t.add_row(ROL_AD[r], "[dim]seçilmedi[/]", "", "")
    analiz = Text("\n".join("• " + n for n in profil.notlar()))
    konsol.print(Panel(Group(t, Text(""), analiz), border_style="red"))

    # Öneriler
    if oneriler:
        o = Table(box=box.SIMPLE_HEAD, expand=True, header_style="bold",
                  title="Sana önerilen şampiyonlar", title_style="bold green")
        o.add_column("#", width=3)
        o.add_column("Şampiyon", min_width=12)
        o.add_column("Puan", justify="right", width=6)
        o.add_column("Neden")
        for i, x in enumerate(oneriler, 1):
            neden = "\n".join(f"[{'green' if d >= 0 else 'red'}]{'+' if d >= 0 else '−'}[/] {n}"
                              for d, n in x.ana_nedenler()) or "[dim]genel uyum[/]"
            o.add_row(str(i), f"[bold]{x.sampiyon.ad}[/]", f"{x.puan:.0f}", neden)
        konsol.print(Panel(o, border_style="green"))
    elif not benim:
        konsol.print(Panel("[dim]Bu koridor için uygun aday bulunamadı.[/]", border_style="green"))

    # Build
    if build and (benim or oneriler):
        hedef = benim or oneriler[0].sampiyon
        ust = f"Build: [bold]{hedef.ad}[/] ({build.arketip})"
        if not benim:
            ust += "  [dim](1. öneri için — şampiyonunu seçince güncellenir)[/]"
        elif benim_kilitli:
            ust += "  [green]✓ kilitlendi[/]"
        b = Table(box=None, expand=True, show_header=False, padding=(0, 1))
        b.add_column(width=6)
        b.add_column(min_width=26)
        b.add_column()
        bas = ", ".join(f"{ad}{' x' + str(n) if n > 1 else ''}" for _, ad, n in build.baslangic)
        b.add_row("[bold]Başla[/]", bas, "")
        if build.bot:
            b.add_row("[bold]Bot[/]", build.bot[1], f"[dim]{build.bot[2]}[/]")
        for i, (_, ad, neden) in enumerate(build.esyalar, 1):
            renk = "dim" if neden in ("Çekirdek", "Geç oyun") else "yellow"
            b.add_row(f"{i}.", f"[bold]{ad}[/]", f"[{renk}]{neden}[/]")
        parcalar = [b]
        if build.b_plani:
            bp = Table(box=None, expand=True, show_header=False, padding=(0, 1))
            bp.add_column(ratio=3)
            bp.add_column(ratio=2)
            for kosul, _, ad in build.b_plani:
                bp.add_row(f"[dim]Eğer[/] {kosul}", f"→ [bold magenta]{ad}[/]")
            parcalar += [Text(""), Text("B PLANI (maçta Tab'a bakıp kendin karar ver)", style="bold magenta"), bp]
        if build.notlar:
            parcalar += [Text(""), Text("\n".join("💡 " + n for n in build.notlar), style="cyan")]
        konsol.print(Panel(Group(*parcalar), title=ust, title_align="left", border_style="gold1"))


def mac_icinde():
    bekle("Maç devam ediyor 🎮\n\n"
          "Riot kuralları gereği program maç sırasında hiçbir analiz yapmaz.\n"
          "Seçim ekranında gösterilen B PLANI mağazadaki eşya setinde duruyor:\n"
          "Tab'a bak, kararı sen ver.\n\n"
          "[dim]Maç bitince 'ne daha iyi olabilirdi' analizi burada görünecek.[/]")


def mac_sonu_goster(mac, dosya=None):
    konsol.clear()
    konsol.rule(f"[bold gold1]Maç Sonu Analizi[/]  ·  {mac.ozet}", style="gold1")
    simge = {"iyi": "[green]✓[/]", "uyari": "[yellow]![/]", "bilgi": "[cyan]i[/]"}
    t = Table(box=None, show_header=False, expand=True, padding=(0, 1))
    t.add_column(width=2)
    t.add_column()
    for tur, m in mac.analiz:
        t.add_row(simge[tur], m)
    alt = f"[dim]Kaydedildi: {dosya}[/]" if dosya else ""
    konsol.print(Panel(t, border_style="gold1", subtitle=alt))
    konsol.print("[dim]Yeni maç bulunduğunda seçim ekranı analizi otomatik başlar.[/]")
