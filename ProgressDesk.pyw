from task_tracker import ProgressDesk, enable_dpi_awareness


if __name__ == "__main__":
    enable_dpi_awareness()
    app = ProgressDesk()
    app.mainloop()
