test: test_helpers test_list test_show test_read test_monitor

test_helpers:
	python srdptool.py --check
	python srdptool.py --uuid 3

test_list:
	python srdptool.py -t udp 192.168.56.102:1910 --list
	python srdptool.py -t serial com12:115200 --list

test_show:
	python srdptool.py -t serial com12:115200 --show 1
	python srdptool.py -t serial com12:115200 --show 2
	python srdptool.py -t serial com12:115200 --show 3
	python srdptool.py -t serial com12:115200 --show 4

test_read:
	python srdptool.py -t serial com12:115200 --read 1
	python srdptool.py -t serial com12:115200 --read 2
	python srdptool.py -t serial com12:115200 --read 3
	python srdptool.py -t serial com12:115200 --read 4

test_monitor:
	python srdptool.py -t serial com12:115200 --monitor 3 --write 1026 1 --write 1029 1 --write 1024 1
