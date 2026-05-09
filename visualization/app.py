import tkinter as tk

from .home_page import HomePage
from .simulation_page import SimulationPage


class VisualizationApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Protocol Visualization Lab")
        self.root.geometry("900x680")
        self.root.configure(bg="#121417")
        self.current_page = None

    def show_home_page(self):
        self._set_page(HomePage(self.root, on_select_protocol=self.show_simulation_page))

    def show_simulation_page(self, protocol):
        self._set_page(SimulationPage(self.root, protocol=protocol, on_back=self.show_home_page))

    def _set_page(self, page):
        if self.current_page is not None:
            self.current_page.destroy()
        self.current_page = page
        self.current_page.pack(fill="both", expand=True)

    def run(self):
        self.show_home_page()
        self.root.mainloop()


def main():
    app = VisualizationApp()
    app.run()


if __name__ == "__main__":
    main()
