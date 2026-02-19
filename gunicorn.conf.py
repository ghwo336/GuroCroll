def post_worker_init(worker):
    """워커 프로세스 초기화 후 백그라운드 로딩 시작"""
    import app as main_app
    main_app.start_background()
