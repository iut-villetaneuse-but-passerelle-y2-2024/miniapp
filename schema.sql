CREATE TABLE miniapp_data(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	status CHAR(1),
	created_at TIMESTAMP,
	update_at TIMESTAMP,
	event CHAR(8)
);
