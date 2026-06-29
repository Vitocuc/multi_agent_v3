import { Box, Heading, Text, Container, VStack, Badge } from '@chakra-ui/react';

export default function HomePage() {
  return (
    <Container maxW="container.lg" py={16}>
      <VStack spacing={8} align="center" textAlign="center">
        <Badge colorScheme="blue" fontSize="sm" px={3} py={1} borderRadius="full">
          Beta
        </Badge>
        <Heading as="h1" size="2xl" color="brand.500">
          Protego Life Simulator
        </Heading>
        <Text fontSize="xl" color="gray.600" maxW="600px">
          Allena la tua disciplina finanziaria con il simulatore comportamentale.
          Nessun denaro reale — solo crescita personale.
        </Text>
        <Box
          bg="brand.50"
          borderRadius="xl"
          p={8}
          border="1px solid"
          borderColor="brand.100"
          maxW="500px"
          w="full"
        >
          <Text fontWeight="semibold" color="brand.700">
            🛡️ Inizia il tuo percorso di consapevolezza finanziaria
          </Text>
          <Text mt={2} color="gray.600" fontSize="sm">
            Accedi con Google per iniziare la simulazione
          </Text>
        </Box>
      </VStack>
    </Container>
  );
}
