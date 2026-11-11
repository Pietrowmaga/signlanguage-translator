-- MariaDB dump 10.19  Distrib 10.4.32-MariaDB, for Win64 (AMD64)
--
-- Host: localhost    Database: signlanguage_db
-- ------------------------------------------------------
-- Server version	10.4.32-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `translation_history`
--

DROP TABLE IF EXISTS `translation_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `translation_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `session_id` int(11) NOT NULL,
  `word` varchar(100) NOT NULL,
  `confidence` float DEFAULT NULL,
  `detected_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `session_id` (`session_id`),
  CONSTRAINT `translation_history_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `translation_sessions` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `translation_history`
--

LOCK TABLES `translation_history` WRITE;
/*!40000 ALTER TABLE `translation_history` DISABLE KEYS */;
INSERT INTO `translation_history` VALUES (1,1,'ILoveYou',0.775183,'2026-09-13 08:45:43'),(2,1,'__none__',0,'2026-09-13 08:46:15'),(3,2,'__none__',0,'2026-09-13 09:06:23'),(4,2,'ILoveYou',0.80527,'2026-09-13 09:06:37'),(5,3,'__none__',0,'2026-09-14 04:31:24'),(6,4,'__none__',0,'2026-09-14 04:50:11'),(7,4,'ILoveYou',0.734229,'2026-09-14 04:50:12'),(8,4,'__none__',0,'2026-09-14 04:50:18'),(9,4,'ILoveYou',0.844506,'2026-09-14 04:50:27'),(10,4,'__none__',0,'2026-09-14 04:50:30'),(11,4,'ILoveYou',0.916058,'2026-09-14 04:50:36'),(12,4,'__none__',0,'2026-09-14 04:50:45'),(13,4,'ILoveYou',0.77166,'2026-09-14 04:51:00'),(14,4,'__none__',0,'2026-09-14 04:51:29'),(15,4,'ILoveYou',0.886688,'2026-09-14 04:51:30'),(16,4,'__none__',0,'2026-09-14 04:51:36'),(17,4,'ILoveYou',0.748238,'2026-09-14 04:51:37');
/*!40000 ALTER TABLE `translation_history` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `translation_sessions`
--

DROP TABLE IF EXISTS `translation_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `translation_sessions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `started_at` datetime DEFAULT NULL,
  `ended_at` datetime DEFAULT NULL,
  `word_count` int(11) DEFAULT NULL,
  `result_text` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `translation_sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `translation_sessions`
--

LOCK TABLES `translation_sessions` WRITE;
/*!40000 ALTER TABLE `translation_sessions` DISABLE KEYS */;
INSERT INTO `translation_sessions` VALUES (1,1,'2026-09-13 08:45:29',NULL,2,''),(2,1,'2026-09-13 09:06:10','2026-09-13 09:06:46',2,'__none__ ILoveYou'),(3,1,'2026-09-14 04:30:41','2026-09-14 04:31:39',1,'__none__'),(4,1,'2026-09-14 04:49:54','2026-09-14 04:51:44',12,'__none__ ILoveYou __none__ ILoveYou __none__ ILoveYou __none__ ILoveYou __none__ ILoveYou __none__ ILoveYou'),(5,1,'2026-09-14 05:42:26',NULL,0,'');
/*!40000 ALTER TABLE `translation_sessions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(80) NOT NULL,
  `email` varchar(120) NOT NULL,
  `password_hash` varchar(256) NOT NULL,
  `avatar_color` varchar(20) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `practice_score` int(11) DEFAULT 0,
  `practice_streak` int(11) DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'siswa','bimoaditiya296@gmail.com','scrypt:32768:8:1$vhe3y0JUwXOz8i1F$7f29fd98f9008b21ffac53de30a3267efb80528065979f168958ee07261f843a0afd069baee2dda086898370aaa33de76f7202ebef56030775aae7be5bcd428b','#a855f7','2026-09-13 08:45:26',0,0);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-14 12:43:04
