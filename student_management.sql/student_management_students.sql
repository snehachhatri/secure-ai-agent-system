-- MySQL dump 10.13  Distrib 8.0.43, for Win64 (x86_64)
--
-- Host: localhost    Database: student_management
-- ------------------------------------------------------
-- Server version	8.0.43

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `students`
--

DROP TABLE IF EXISTS `students`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `students` (
  `student_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `course` varchar(100) DEFAULT NULL,
  `department_id` int DEFAULT NULL,
  `semester` int DEFAULT NULL,
  `gender` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`student_id`),
  UNIQUE KEY `email` (`email`),
  KEY `department_id` (`department_id`),
  CONSTRAINT `students_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `departments` (`department_id`)
) ENGINE=InnoDB AUTO_INCREMENT=51 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `students`
--

LOCK TABLES `students` WRITE;
/*!40000 ALTER TABLE `students` DISABLE KEYS */;
INSERT INTO `students` VALUES (1,'Rahul Sharma','rahul.student@example.com','B.Tech CSE',1,7,'Male'),(2,'Priya Verma','priya.student@example.com','B.Tech CSE',1,7,'Female'),(3,'Aarav Patil','aarav.student@example.com','B.Tech IT',2,7,'Male'),(4,'Sneha Joshi','sneha.student@example.com','B.Tech CSE',1,7,'Female'),(5,'Karan Rao','karan.student@example.com','B.Tech Electronics',3,7,'Male'),(6,'Student 06','student06@example.com','General',1,7,'Female'),(7,'Student 07','student07@example.com','General',1,7,'Female'),(8,'Student 08','student08@example.com','General',1,7,'Male'),(9,'Student 09','student09@example.com','General',1,7,'Male'),(10,'Student 10','student10@example.com','General',1,7,'Female'),(11,'Student 11','student11@example.com','General',1,7,'Male'),(12,'Student 12','student12@example.com','General',1,7,'Male'),(13,'Student 13','student13@example.com','General',1,7,'Female'),(14,'Student 14','student14@example.com','General',1,7,'Male'),(15,'Student 15','student15@example.com','General',1,7,'Female'),(16,'Student 16','student16@example.com','General',1,7,'Female'),(17,'Student 17','student17@example.com','General',1,7,'Male'),(18,'Student 18','student18@example.com','General',1,7,'Female'),(19,'Student 19','student19@example.com','General',1,7,'Male'),(20,'Student 20','student20@example.com','General',1,7,'Female'),(21,'Student 21','student21@example.com','General',1,7,'Male'),(22,'Student 22','student22@example.com','General',1,7,'Female'),(23,'Student 23','student23@example.com','General',1,7,'Male'),(24,'Student 24','student24@example.com','General',1,7,'Female'),(25,'Student 25','student25@example.com','General',1,7,'Male'),(26,'Student 26','student26@example.com','General',1,7,'Male'),(27,'Student 27','student27@example.com','General',1,7,'Male'),(28,'Student 28','student28@example.com','General',1,7,'Female'),(29,'Student 29','student29@example.com','General',1,7,'Male'),(30,'Student 30','student30@example.com','General',1,7,'Female'),(31,'Student 31','student31@example.com','General',1,7,'Female'),(32,'Student 32','student32@example.com','General',1,7,'Female'),(33,'Student 33','student33@example.com','General',1,7,'Female'),(34,'Student 34','student34@example.com','General',1,7,'Male'),(35,'Student 35','student35@example.com','General',1,7,'Male'),(36,'Student 36','student36@example.com','General',1,7,'Male'),(37,'Student 37','student37@example.com','General',1,7,'Female'),(38,'Student 38','student38@example.com','General',1,7,'Female'),(39,'Student 39','student39@example.com','General',1,7,'Female'),(40,'Student 40','student40@example.com','General',1,7,'Male'),(41,'Student 41','student41@example.com','General',1,7,'Male'),(42,'Student 42','student42@example.com','General',1,7,'Female'),(43,'Student 43','student43@example.com','General',1,7,'Female'),(44,'Student 44','student44@example.com','General',1,7,'Male'),(45,'Student 45','student45@example.com','General',1,7,'Female'),(46,'Student 46','student46@example.com','General',1,7,'Male'),(47,'Student 47','student47@example.com','General',1,7,'Female'),(48,'Student 48','student48@example.com','General',1,7,'Female'),(49,'Student 49','student49@example.com','General',1,7,'Female'),(50,'Student 50','student50@example.com','General',1,7,'Male');
/*!40000 ALTER TABLE `students` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-14 17:08:32
